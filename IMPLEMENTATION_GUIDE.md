# 照片系统和支付集成 - 实施指南

## 📸 照片系统

### 后端实现

#### 1. 数据模型
- **文件**: `backend/app/models/user_photo.py`
- **表名**: `user_photos`
- **主要字段**:
  - `file_path`: 文件存储路径
  - `file_url`: 访问URL
  - `display_order`: 显示顺序
  - `is_primary`: 是否为主照片
  - `status`: 审核状态（pending/approved/rejected）

#### 2. API端点
- **文件**: `backend/app/api/v1/endpoints/photos.py`
- **端点**:
  - `POST /api/v1/photos/upload` - 上传照片
  - `GET /api/v1/photos/me` - 获取我的照片
  - `GET /api/v1/photos/{photo_id}` - 获取单张照片
  - `GET /api/v1/photos/file/{filename}` - 获取照片文件
  - `PUT /api/v1/photos/{photo_id}` - 更新照片（设置主照片）
  - `POST /api/v1/photos/reorder` - 重新排序照片
  - `DELETE /api/v1/photos/{photo_id}` - 删除照片

#### 3. 配置
- **文件**: `backend/app/core/config.py`
- **配置项**:
  - `UPLOAD_DIR`: 上传文件目录（默认: "uploads"）
  - `MAX_PHOTO_SIZE`: 最大照片大小（默认: 10MB）
  - `ALLOWED_PHOTO_TYPES`: 允许的文件类型
  - `PHOTOS_PER_USER`: 每个用户最多照片数（默认: 9）

#### 4. 文件存储
- 照片存储在 `uploads/photos/` 目录
- 文件名格式: `{user_id}_{uuid}.{ext}`
- 开发环境使用本地存储，生产环境建议使用云存储（OSS/S3）

### 前端实现

#### 1. 照片上传组件
- **文件**: `uae-match-web/src/components/profile/photo-upload.tsx`
- **功能**:
  - 照片上传（拖拽或点击）
  - 照片预览
  - 设置主照片
  - 删除照片
  - 照片排序

#### 2. 使用示例
```tsx
import { PhotoUpload } from "@/components/profile/photo-upload";

function ProfilePage() {
  const [photos, setPhotos] = useState([]);
  
  return (
    <PhotoUpload
      photos={photos}
      onPhotosChange={setPhotos}
      maxPhotos={9}
    />
  );
}
```

### 数据库迁移

运行以下命令创建新表：
```bash
cd backend
python -c "from app.db.session import engine; from app.db import base; base.Base.metadata.create_all(bind=engine)"
```

或使用 Alembic（推荐）：
```bash
alembic revision --autogenerate -m "add user_photos table"
alembic upgrade head
```

---

## 💳 支付集成

### 后端实现

#### 1. 数据模型
- **文件**: `backend/app/models/order.py`
- **表名**: `orders`, `subscriptions`
- **主要字段**:
  - `Order`: 订单信息（订单号、金额、支付状态等）
  - `Subscription`: 订阅信息（会员类型、到期时间等）

#### 2. API端点
- **文件**: `backend/app/api/v1/endpoints/payment.py`
- **端点**:
  - `POST /api/v1/payment/create-order` - 创建订单
  - `POST /api/v1/payment/callback` - 支付回调
  - `GET /api/v1/payment/orders/me` - 获取我的订单
  - `GET /api/v1/payment/orders/{order_no}` - 获取订单详情
  - `GET /api/v1/payment/subscription/status` - 获取订阅状态
  - `GET /api/v1/payment/products` - 获取产品列表

#### 3. 产品配置
- **会员套餐**:
  - `basic_monthly`: 普通会员（月付）¥29
  - `basic_yearly`: 普通会员（年付）¥299
  - `premium_monthly`: 高级会员（月付）¥59
  - `premium_yearly`: 高级会员（年付）¥599
- **增值服务**:
  - `super_like`: 超级喜欢 ¥5
  - `boost`: 提升曝光度 ¥19
  - `who_liked_me`: 查看谁喜欢我 ¥9

#### 4. 支付集成（待实现）
目前支付回调是模拟的，需要集成实际的支付SDK：
- **支付宝**: 使用 `alipay-sdk-python`
- **微信支付**: 使用 `wechatpay-python`
- **配置**: 在 `config.py` 中添加支付配置

### 前端实现

#### 1. 会员中心页面
- **文件**: `uae-match-web/src/app/premium/page.tsx`
- **功能**:
  - 显示当前订阅状态
  - 会员套餐展示和购买
  - 增值服务购买

#### 2. 使用示例
访问 `/premium` 页面即可看到会员中心。

### 数据库迁移

运行以下命令创建新表：
```bash
cd backend
python -c "from app.db.session import engine; from app.db import base; base.Base.metadata.create_all(bind=engine)"
```

---

## 🔧 安装依赖

### 后端
```bash
cd backend
pip install -r requirements.txt
```

新增依赖：
- `Pillow==10.1.0` - 图片处理

### 前端
无需新增依赖，使用现有组件。

---

## 📝 使用说明

### 照片系统

1. **上传照片**:
   - 在个人资料页面使用 `PhotoUpload` 组件
   - 支持拖拽或点击上传
   - 自动验证文件类型和大小

2. **管理照片**:
   - 点击照片可设置为主照片
   - 删除不需要的照片
   - 照片自动按顺序排列

3. **照片审核**:
   - 上传后状态为 `pending`
   - 管理员可在后台审核
   - 审核通过后状态变为 `approved`

### 支付系统

1. **购买会员**:
   - 访问 `/premium` 页面
   - 选择会员套餐
   - 点击"立即购买"创建订单

2. **查看订阅状态**:
   - 在会员中心查看当前订阅
   - 查看剩余天数
   - 查看到期时间

3. **购买增值服务**:
   - 在会员中心选择增值服务
   - 点击"购买"创建订单
   - 完成支付后立即生效

---

## ⚠️ 注意事项

### 照片系统

1. **文件存储**:
   - 开发环境使用本地存储
   - 生产环境建议使用云存储（阿里云OSS、AWS S3等）
   - 需要配置CDN加速图片访问

2. **图片处理**:
   - 建议添加图片压缩
   - 生成缩略图
   - 支持图片裁剪

3. **安全**:
   - 验证文件类型和大小
   - 防止恶意文件上传
   - 图片审核机制

### 支付系统

1. **支付集成**:
   - 当前是模拟实现
   - 需要集成实际的支付SDK
   - 配置支付回调URL

2. **订单管理**:
   - 实现订单查询
   - 处理退款
   - 订单统计

3. **订阅管理**:
   - 自动续费逻辑
   - 订阅到期提醒
   - 订阅取消处理

---

## 🚀 下一步

1. **照片系统**:
   - [ ] 集成云存储（OSS/S3）
   - [ ] 添加图片压缩和缩略图
   - [ ] 实现图片审核功能
   - [ ] 添加真人认证功能

2. **支付系统**:
   - [ ] 集成支付宝SDK
   - [ ] 集成微信支付SDK
   - [ ] 实现支付回调处理
   - [ ] 添加订单管理页面
   - [ ] 实现自动续费逻辑

3. **会员功能**:
   - [ ] 实现会员特权（无限匹配、查看谁喜欢我等）
   - [ ] 添加会员标识显示
   - [ ] 实现高级筛选功能
