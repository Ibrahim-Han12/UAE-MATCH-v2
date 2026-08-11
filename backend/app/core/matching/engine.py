"""
匹配引擎（算法文档 v0.4 的工程实现；BR-306 / PRD 6.1 T-3 计算）。

四段漏斗：Stage0 资格 → Stage1 硬约束(双向布尔+弹性语义) → Stage2 五维计分
        → Stage3 语义调整(±5) → pair_score=min(双向) → 阈值 → 分配约束。
可解释铁律：每个 pair 输出 triggered_rules / dimensions / highlight_fields /
friction_point 的完整 breakdown（§7 契约），无 breakdown 即黑盒。
v1 量级：全量两两计算、周批离线，无索引/召回架构（禁过度设计）。
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.matching.config import load as load_config
from app.core.embedding_service import get_embedding_service
from app.models.user import User
from app.models.profile import UserProfile
from app.models.match_preference import MatchPreference
from app.models.user_psych_profile import UserPsychProfile
from app.models.user_embedding import UserEmbedding
from app.models.user_block import UserBlock
from app.models.match_pair import MatchPair
from app.models.reco_pair import RecoPair

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """一个进入匹配的用户的全量画像快照。"""
    user: User
    profile: UserProfile
    pref: Optional[MatchPreference]
    psych: Optional[UserPsychProfile]
    vector: Optional[list] = None

    @property
    def uid(self) -> int:
        return self.user.id

    @property
    def age(self) -> Optional[int]:
        from datetime import date
        if self.profile.birth_year:
            return date.today().year - self.profile.birth_year
        return None

    def ext(self, key: str) -> Any:
        return (self.profile.extended_info or {}).get(key)

    def elasticity(self, cid: str) -> str:
        default = load_config()["elasticity"]["default"]
        return ((self.pref.elasticity or {}) if self.pref else {}).get(cid, default)


# ============ Stage 0 · 资格过滤 ============

def load_pool(db: Session) -> List[Candidate]:
    """S3/S4 且画像速写已确认、非冷静期的用户全量载入。"""
    users = (
        db.query(User)
        .filter(User.status.in_(("S3", "S4")), User.is_active.is_(True),
                User.cancellation_requested_at.is_(None))
        .all()
    )
    pool = []
    for u in users:
        p = db.query(UserProfile).filter_by(user_id=u.id).first()
        if p is None or p.sketch_confirmed_at is None or not p.gender:
            continue  # 0.2 速写未确认不进池
        pref = db.query(MatchPreference).filter_by(user_id=u.id).first()
        psych = db.query(UserPsychProfile).filter_by(user_id=u.id).first()
        emb = db.query(UserEmbedding).filter_by(user_id=u.id).first()
        vec = None
        if emb is not None:
            try:
                vec = json.loads(emb.embedding_vector) if isinstance(emb.embedding_vector, str) else emb.embedding_vector
            except Exception:
                vec = None
        pool.append(Candidate(user=u, profile=p, pref=pref, psych=psych, vector=vec))
    return pool


def _load_exclusions(db: Session) -> set:
    """互斥对集合：拉黑(双向)、历史配对、历史已推荐对。返回 {(low,high)}。"""
    excl = set()
    for b in db.query(UserBlock).all():
        excl.add((min(b.blocker_id, b.blocked_id), max(b.blocker_id, b.blocked_id)))
    for m in db.query(MatchPair).all():
        excl.add((min(m.user1_id, m.user2_id), max(m.user1_id, m.user2_id)))
    for r in db.query(RecoPair).all():   # 0.5 简化：历史推荐对一律不重推（重推例外 M3 实现）
        excl.add((r.user_low_id, r.user_high_id))
    return excl


def stage0_pass(a: Candidate, b: Candidate, exclusions: set) -> bool:
    if a.uid == b.uid:
        return False
    if (min(a.uid, b.uid), max(a.uid, b.uid)) in exclusions:
        return False
    # 0.6 性别互补（Q1：UAE 法域合规约束）
    if {a.profile.gender, b.profile.gender} != {"male", "female"}:
        return False
    return True


# ============ Stage 1 · 硬约束（双向） ============

@dataclass
class DirectionCheck:
    passed: bool = True
    negotiable_extensions: int = 0
    preference_unmet: int = 0
    boolean_negotiable: int = 0      # G3：布尔型 negotiable 计数（每个 -3）
    rules: List[str] = field(default_factory=list)


def _edu_rank(cfg: dict, level: Optional[str]) -> Optional[int]:
    return cfg["hard_rules"]["education_rank"].get(level) if level else None


def _check_one_direction(cfg: dict, me: Candidate, other: Candidate) -> DirectionCheck:
    """me 的 C 类条件，other 是否满足。"""
    r = DirectionCheck()
    pref = me.pref
    if pref is None:
        return r
    el = cfg["elasticity"]

    # R1 年龄
    if pref.min_age or pref.max_age:
        age = other.age
        if age is not None:
            lo = pref.min_age or 0
            hi = pref.max_age or 200
            e = me.elasticity("C1")
            if lo <= age <= hi:
                pass
            elif e == "negotiable" and (lo - el["age_extension_years"]) <= age <= (hi + el["age_extension_years"]):
                r.negotiable_extensions += 1
                r.rules.append("C1:negotiable_extended")
            elif e == "preference":
                r.preference_unmet += 1
            else:
                r.passed = False
                r.rules.append("C1:age_filtered")
                return r

    # R2 身高
    if pref.min_height_cm and other.profile.height_cm:
        h = other.profile.height_cm
        e = me.elasticity("C2")
        if h >= pref.min_height_cm:
            pass
        elif e == "negotiable" and h >= pref.min_height_cm - el["height_extension_cm"]:
            r.negotiable_extensions += 1
            r.rules.append("C2:negotiable_extended")
        elif e == "preference":
            r.preference_unmet += 1
        else:
            r.passed = False
            r.rules.append("C2:height_filtered")
            return r

    # R3 学历/收入门槛
    e3 = me.elasticity("C3")
    if pref.education_floor and pref.education_floor != "none":
        floor = _edu_rank(cfg, pref.education_floor)
        actual = _edu_rank(cfg, other.profile.education_level)
        if floor is not None and actual is not None:
            if actual >= floor:
                pass
            elif e3 == "negotiable" and actual >= floor - el["edu_income_notch_down"]:
                r.negotiable_extensions += 1
                r.rules.append("C3:edu_negotiable_extended")
            elif e3 == "preference":
                r.preference_unmet += 1
            else:
                r.passed = False
                r.rules.append("C3:education_filtered")
                return r
    if pref.income_floor_band and pref.income_floor_band != "none":
        floor = cfg["hard_rules"]["income_floor_rank"].get(pref.income_floor_band, -1)
        actual = cfg["hard_rules"]["income_rank"].get(other.profile.income_band_aed)
        if actual is not None and floor >= 0:
            if actual >= floor:
                pass
            elif e3 == "negotiable" and actual >= floor - el["edu_income_notch_down"]:
                r.negotiable_extensions += 1
                r.rules.append("C3:income_negotiable_extended")
            elif e3 == "preference":
                r.preference_unmet += 1
            else:
                r.passed = False
                r.rules.append("C3:income_filtered")
                return r

    # R4 地域（G3：布尔 negotiable=不过滤记-3）
    if pref.same_emirate_only:
        same = (me.profile.residence_emirate and
                me.profile.residence_emirate == other.profile.residence_emirate)
        if not same:
            e4 = me.elasticity("C4")
            if e4 == "hard":
                r.passed = False
                r.rules.append("C4:emirate_filtered")
                return r
            elif e4 == "negotiable":
                r.boolean_negotiable += 1
                r.rules.append("C4:boolean_negotiable(-3)")
            else:
                r.preference_unmet += 1

    # R5 免谈项（per-item 弹性）
    for item in (pref.dealbreakers or []):
        code = item.get("code")
        item_el = item.get("elasticity_value", "hard")
        hit = False
        sd_other = other.ext("smoking_drinking") or {}
        if code == "smoking" and sd_other.get("smoking") not in (None, "never"):
            hit = True
        elif code == "heavy_drinking" and sd_other.get("drinking") == "regularly":
            hit = True
        elif code == "divorced" and other.profile.marital_history == "divorced":
            hit = True
        elif code == "has_children" and (other.profile.has_children or {}).get("has") == "yes":
            hit = True
        # gambling/pets_conflict：仅叙事信号，v1 不触发过滤；long_distance 由 R4 覆盖
        if hit:
            if item_el == "hard":
                r.passed = False
                r.rules.append(f"C5:{code}_filtered")
                return r
            r.negotiable_extensions += 1
            r.rules.append(f"C5:{code}_negotiable")
    return r


def _check_mutual_hard(cfg: dict, a: Candidate, b: Candidate) -> Tuple[bool, List[str]]:
    """双向共同硬约束：R4 跨酋长国 B6、R6 去留、R7 时间线、R8 子女、R9 宗教。"""
    rules: List[str] = []
    hr = cfg["hard_rules"]

    # R4 跨酋长国场景：双方 B6.cross_emirate 须接受
    ea, eb = a.profile.residence_emirate, b.profile.residence_emirate
    if ea and eb and ea != eb:
        for c in (a, b):
            dt = c.profile.distance_tolerance or {}
            if dt.get("cross_emirate") == "no":
                return False, ["R4:cross_emirate_filtered"]
        rules.append("R4:cross_emirate_ok")

    # R6 去留冲突矩阵
    p1, p2 = a.profile.relocation_plan, b.profile.relocation_plan
    if p1 and p2:
        for pair in hr["r6_b1_filter_pairs"]:
            if {p1, p2} == set(pair):
                return False, ["R6:relocation_filtered"]
        if p1 == "return_within_years" and p2 == "return_within_years":
            y1, y2 = a.profile.return_horizon_years, b.profile.return_horizon_years
            if y1 and y2 and abs(y1 - y2) > hr["r6_return_window_max_gap_years"]:
                return False, ["R6:return_window_gap_filtered"]
        rules.append(f"B1:{p1}_x_{p2}")

    # R7 结婚时间线
    t1 = hr["b2_order"].get(a.profile.marriage_timeline)
    t2 = hr["b2_order"].get(b.profile.marriage_timeline)
    if t1 is not None and t2 is not None and abs(t1 - t2) >= hr["r7_timeline_filter_gap"]:
        return False, ["R7:timeline_filtered"]

    # R8 子女计划
    w1 = (a.profile.children_plan or {}).get("want_children")
    w2 = (b.profile.children_plan or {}).get("want_children")
    if {w1, w2} == {"yes", "no"}:
        return False, ["R8:children_want_filtered"]
    for me, other in ((a, b), (b, a)):
        if (other.profile.has_children or {}).get("has") == "yes":
            if (me.profile.children_plan or {}).get("accept_partner_with_children") == "no":
                return False, ["R8:partner_children_filtered"]

    # R9 宗教约束（G4：B5.religion_constraint 为唯一豁免）
    for me, other in ((a, b), (b, a)):
        constraint = ((me.profile.cross_cultural_openness or {}).get("religion_constraint"))
        other_faith = (other.ext("religion") or {}).get("faith")
        if constraint == "same_faith_only" and other_faith:
            my_faith = (me.ext("religion") or {}).get("faith")
            if my_faith and other_faith != my_faith:
                return False, ["R9:religion_filtered"]
        if constraint == "non_muslim_only" and other_faith == "muslim":
            return False, ["R9:religion_filtered"]

    return True, rules


# ============ Stage 2 · 五维计分 ============

def _conf_factor(psych: Optional[UserPsychProfile], key: str, cfg: dict) -> float:
    conf = (psych.field_confidence or {}) if psych else {}
    return cfg["scoring"]["inferred_confidence_factor"] if conf.get(key) == "inferred" else 1.0


def _score_life_plan(cfg: dict, a: Candidate, b: Candidate, rules: List[str]) -> Tuple[float, int]:
    c = cfg["life_plan"]
    subs = []
    p1, p2 = a.profile.relocation_plan, b.profile.relocation_plan
    if p1 and p2:
        lo, hi = sorted([p1, p2])
        f = c["b1_matrix"].get(lo, {}).get(hi) or c["b1_matrix"].get(hi, {}).get(lo) or 0.6
        subs.append(f)
    t1 = cfg["hard_rules"]["b2_order"].get(a.profile.marriage_timeline)
    t2 = cfg["hard_rules"]["b2_order"].get(b.profile.marriage_timeline)
    if t1 is not None and t2 is not None:
        f = c["b2_timeline_factors"].get(abs(t1 - t2), 0.3)
        subs.append(f)
        if abs(t1 - t2) >= 1:
            rules.append(f"B2:timeline_gap_{abs(t1-t2)}")
    w1 = (a.profile.children_plan or {}).get("want_children")
    w2 = (b.profile.children_plan or {}).get("want_children")
    if w1 and w2:
        if w1 == w2:
            subs.append(c["b3_children"]["open_open" if w1 == "open_to_discuss" else "same"])
        else:
            subs.append(c["b3_children"]["yes_open"])
    e1, e2 = a.profile.parents_care_plan, b.profile.parents_care_plan
    if e1 and e2:
        if e1 == e2:
            subs.append(c["b4_elders"]["same"])
        elif {e1, e2} == {"bring_to_uae", "return_to_care"}:
            subs.append(c["b4_elders"]["conflict_bring_vs_return"])
            rules.append("B4:elders_conflict")
        else:
            subs.append(c["b4_elders"]["other"])
    total = cfg["scoring"]["dimensions"]["life_plan"]
    return ((sum(subs) / len(subs)) * total if subs else total * 0.5), len(subs)


def _score_psych(cfg: dict, a: Candidate, b: Candidate, rules: List[str]) -> Tuple[float, int]:
    c = cfg["psych"]
    subs = []
    pa, pb = a.psych, b.psych
    if pa and pb:
        d1a, d1b = pa.attachment_style, pb.attachment_style
        if d1a and d1b:
            lo, hi = sorted([d1a, d1b])
            f = c["d1_attachment_matrix"].get(lo, {}).get(hi) or c["d1_attachment_matrix"].get(hi, {}).get(lo) or 0.7
            f *= _conf_factor(pa, "attachment_style", cfg) * _conf_factor(pb, "attachment_style", cfg)
            subs.append(f)
            rules.append(f"D1:{lo}_x_{hi}")
        d2a, d2b = pa.conflict_style, pb.conflict_style
        if d2a and d2b:
            lo, hi = sorted([d2a, d2b])
            f = c["d2_conflict_matrix"].get(lo, {}).get(hi) or c["d2_conflict_matrix"].get(hi, {}).get(lo) or 0.6
            subs.append(f)
    score = (sum(subs) / len(subs)) if subs else 0.6
    # 双高神经质（BR-306）
    if pa and pb and pa.big_five_neuroticism and pb.big_five_neuroticism:
        th = c["neuroticism_high_threshold"]
        if pa.big_five_neuroticism > th and pb.big_five_neuroticism > th:
            score *= c["neuroticism_double_high_factor"]
            rules.append("E1:double_high_neuroticism")
    # 尽责性差距（G2）
    if pa and pb and pa.big_five_conscientiousness is not None and pb.big_five_conscientiousness is not None:
        if abs(pa.big_five_conscientiousness - pb.big_five_conscientiousness) > c["conscientiousness_gap_threshold"]:
            score *= c["conscientiousness_gap_factor"]
            rules.append("E1:conscientiousness_gap")
    return score * cfg["scoring"]["dimensions"]["psych"], len(subs)


def _score_values(cfg: dict, a: Candidate, b: Candidate, rules: List[str]) -> Tuple[float, int]:
    c = cfg["values"]
    subs = []
    fa = (a.psych.family_role_expectation or {}) if a.psych else {}
    fb = (b.psych.family_role_expectation or {}) if b.psych else {}
    for key in ("finance_model", "career_priority", "housework_expectation"):
        v1, v2 = fa.get(key), fb.get(key)
        if v1 and v2:
            if v1 == v2:
                subs.append(c["d3_subitem"]["same"])
            elif "flexible" in (v1, v2) or "undecided" in (v1, v2):
                subs.append(c["d3_subitem"]["one_flexible"])
            else:
                subs.append(c["d3_subitem"]["differ"])
    m1 = a.psych.money_view if a.psych else None
    m2 = b.psych.money_view if b.psych else None
    if m1 and m2:
        lo, hi = sorted([m1, m2])
        f = c["d4_money_matrix"].get(lo, {}).get(hi) or c["d4_money_matrix"].get(hi, {}).get(lo) or 0.7
        subs.append(f)
        if f <= 0.3:
            rules.append("D4:money_view_clash")
    r1 = (a.ext("religion") or {}).get("practice_level")
    r2 = (b.ext("religion") or {}).get("practice_level")
    if r1 and r2 and r1 == r2:
        subs.append(c["e6_practice_same_bonus"])
    total = cfg["scoring"]["dimensions"]["values"]
    return ((sum(subs) / len(subs)) * total if subs else total * 0.5), len(subs)


def _score_lifestyle(cfg: dict, a: Candidate, b: Candidate, highlights: List[str]) -> Tuple[float, int]:
    c = cfg["lifestyle"]
    subs = []
    r1, r2 = a.ext("daily_rhythm"), b.ext("daily_rhythm")
    if r1 and r2:
        subs.append(c["e3_rhythm"]["same"] if r1 == r2 else (c["e3_rhythm"]["flexible"] if "flexible" in (r1, r2) else c["e3_rhythm"]["differ"]))
    order = {"never": 0, "socially": 1, "regularly": 2}
    sda, sdb = a.ext("smoking_drinking") or {}, b.ext("smoking_drinking") or {}
    diffs = [abs(order[sda[k]] - order[sdb[k]]) for k in ("smoking", "drinking")
             if sda.get(k) in order and sdb.get(k) in order]
    if diffs:
        subs.append(sum(c["e5_diff_factors"].get(d, 0.2) for d in diffs) / len(diffs))
    so = {"homebody": 0, "small_circle": 1, "active_social": 2}
    s1, s2 = a.ext("social_radius"), b.ext("social_radius")
    if s1 in so and s2 in so:
        subs.append(c["e7_diff_factors"].get(abs(so[s1] - so[s2]), 0.3))
    t1, t2 = set(a.ext("interest_tags") or []), set(b.ext("interest_tags") or [])
    if t1 and t2:
        overlap = t1 & t2
        subs.append(min(1.0, len(overlap) / c["e8_overlap_divisor"]))
        for tag in list(overlap)[:2]:
            highlights.append(f"E8:{tag}")
    ea, eb = a.profile.residence_emirate, b.profile.residence_emirate
    if ea and eb:
        if ea == eb and a.profile.residence_district and a.profile.residence_district == b.profile.residence_district:
            subs.append(c["a8_distance"]["same_district"])
        elif ea == eb:
            subs.append(c["a8_distance"]["same_emirate"])
        else:
            subs.append(c["a8_distance"]["cross_emirate"])
    total = cfg["scoring"]["dimensions"]["lifestyle"]
    return ((sum(subs) / len(subs)) * total if subs else total * 0.5), len(subs)


def _score_condition_fit(cfg: dict, ca: DirectionCheck, cb: DirectionCheck) -> float:
    c = cfg["condition_fit"]
    penalty = min(c["negotiable_penalty_cap"],
                  (ca.negotiable_extensions + cb.negotiable_extensions) * c["negotiable_extension_penalty"])
    penalty += (ca.preference_unmet + cb.preference_unmet) * c["preference_unmet_penalty"]
    penalty += (ca.boolean_negotiable + cb.boolean_negotiable) * cfg["elasticity"]["boolean_negotiable_penalty"]
    return max(0.0, c["base"] - penalty)


def _semantic_bonus(cfg: dict, a: Candidate, b: Candidate) -> int:
    if not a.vector or not b.vector:
        return 0
    try:
        sim = get_embedding_service().cosine_similarity(a.vector, b.vector)
    except Exception:
        return 0
    return round(max(0.0, min(1.0, sim)) * cfg["scoring"]["semantic_bonus_max"])


# ============ 综合 ============

def compute_pair(db: Session, a: Candidate, b: Candidate) -> Optional[Dict[str, Any]]:
    """完整计算一对。不达 Stage1 返回 None；否则返回 §7 契约 breakdown。"""
    cfg = load_config()

    ok, mutual_rules = _check_mutual_hard(cfg, a, b)
    if not ok:
        return None
    ca = _check_one_direction(cfg, a, b)
    if not ca.passed:
        return None
    cb = _check_one_direction(cfg, b, a)
    if not cb.passed:
        return None

    rules: List[str] = mutual_rules + ca.rules + cb.rules
    highlights: List[str] = []

    life, n1 = _score_life_plan(cfg, a, b, rules)
    psych, n2 = _score_psych(cfg, a, b, rules)
    values, n3 = _score_values(cfg, a, b, rules)
    lifestyle, n4 = _score_lifestyle(cfg, a, b, highlights)
    cond = _score_condition_fit(cfg, ca, cb)
    bonus = _semantic_bonus(cfg, a, b)

    base = life + psych + values + lifestyle
    # 双向体验对等：条件满足度按各自方向计入后取 min
    score_a2b = round(base + max(0.0, cfg["condition_fit"]["base"]
                                 - ca.negotiable_extensions * cfg["condition_fit"]["negotiable_extension_penalty"]
                                 - ca.preference_unmet * cfg["condition_fit"]["preference_unmet_penalty"]
                                 - ca.boolean_negotiable * cfg["elasticity"]["boolean_negotiable_penalty"]) + bonus)
    score_b2a = round(base + max(0.0, cfg["condition_fit"]["base"]
                                 - cb.negotiable_extensions * cfg["condition_fit"]["negotiable_extension_penalty"]
                                 - cb.preference_unmet * cfg["condition_fit"]["preference_unmet_penalty"]
                                 - cb.boolean_negotiable * cfg["elasticity"]["boolean_negotiable_penalty"]) + bonus)
    pair_score = min(score_a2b, score_b2a)

    # 高亮字段（推荐语素材，BR-307）：同向的 B1/B2 + 兴趣交集
    if a.profile.relocation_plan and a.profile.relocation_plan == b.profile.relocation_plan:
        highlights.insert(0, "B1")
    if a.profile.marriage_timeline and a.profile.marriage_timeline == b.profile.marriage_timeline:
        highlights.insert(0, "B2")

    # 诚实差异点（PRD 6.2-④）：取一条非过滤级摩擦
    friction = next((r for r in rules if "gap" in r or "conflict" in r or "clash" in r), None)

    total_subs = n1 + n2 + n3 + n4
    confidence = round(min(1.0, total_subs / 10.0), 2)  # 数据完备率（10 个子项为满）

    return {
        "score": pair_score,
        "direction_scores": {"a_to_b": score_a2b, "b_to_a": score_b2a},
        "confidence": confidence,
        "dimensions": {"life_plan": round(life, 1), "psych": round(psych, 1),
                       "values": round(values, 1), "lifestyle": round(lifestyle, 1),
                       "condition_fit": round(cond, 1)},
        "semantic_bonus": bonus,
        "triggered_rules": rules,
        "highlight_fields": highlights[:5],
        "friction_point": friction,
    }


def run_stage_t3(db: Session, batch_id: str) -> Dict[str, int]:
    """T-3 全量计算 → 达阈值 pair 入草稿队列（幂等：同批次同对不重建）。"""
    cfg = load_config()
    pool = load_pool(db)
    exclusions = _load_exclusions(db)

    threshold = cfg["thresholds"]["steady_state"]
    floor = cfg["thresholds"]["grey_zone_floor"]
    if len(pool) < cfg["thresholds"]["cold_start_pool_size"]:
        threshold = cfg["thresholds"]["cold_start"]
        floor = cfg["thresholds"]["cold_grey_floor"]
    floor = max(floor, cfg["thresholds"]["absolute_floor"])

    scored: List[Tuple[int, Candidate, Candidate, dict]] = []
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            a, b = pool[i], pool[j]
            if not stage0_pass(a, b, exclusions):
                continue
            breakdown = compute_pair(db, a, b)
            if breakdown is None:
                continue
            if breakdown["score"] >= floor:
                scored.append((breakdown["score"], a, b, breakdown))

    # 分配约束：按分降序贪心，双方本批次配额 <3（Q3 与接收上限对称，pair 模型下二者合一）
    scored.sort(key=lambda x: -x[0])
    week_count: Dict[int, int] = {}
    cap = cfg["allocation"]["max_letters_per_user_per_week"]
    created = 0
    for score, a, b, br in scored:
        if week_count.get(a.uid, 0) >= cap or week_count.get(b.uid, 0) >= cap:
            continue
        lo, hi = min(a.uid, b.uid), max(a.uid, b.uid)
        exists = db.query(RecoPair).filter_by(batch_id=batch_id, user_low_id=lo, user_high_id=hi).first()
        if exists:
            week_count[a.uid] = week_count.get(a.uid, 0) + 1
            week_count[b.uid] = week_count.get(b.uid, 0) + 1
            continue
        db.add(RecoPair(
            batch_id=batch_id, user_low_id=lo, user_high_id=hi,
            score=score, direction_scores=br["direction_scores"], confidence=br["confidence"],
            dimensions=br["dimensions"], semantic_bonus=br["semantic_bonus"],
            triggered_rules=br["triggered_rules"], highlight_fields=br["highlight_fields"],
            friction_point=br["friction_point"],
            status="draft",
        ))
        week_count[a.uid] = week_count.get(a.uid, 0) + 1
        week_count[b.uid] = week_count.get(b.uid, 0) + 1
        created += 1

    logger.info("T-3 batch=%s pool=%d scored=%d created=%d threshold=%d",
                batch_id, len(pool), len(scored), created, threshold)
    return {"pool": len(pool), "qualified": len(scored), "created": created,
            "threshold": threshold, "floor": floor}
