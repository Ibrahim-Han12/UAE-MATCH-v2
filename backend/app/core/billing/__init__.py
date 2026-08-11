"""
订阅计费（⑥，BR-501/502/503）。

catalog  —— config/products.yaml 商品目录（价格唯一来源）
provider —— 支付通道适配器（mock / stripe 骨架，平台不碰卡号）
service  —— 订阅生命周期（激活 S3→S4 / 取消周期末 / 失败宽限 / 到期降级 S4→S3）
"""
from app.core.billing import catalog, provider, service  # noqa: F401
