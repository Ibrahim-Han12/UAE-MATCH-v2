from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    product_type: str = Field(..., description="产品类型: subscription / premium_feature")
    product_id: str = Field(..., description="产品ID")
    product_name: str = Field(..., description="产品名称")
    amount: Decimal = Field(..., description="金额")
    currency: str = Field(default="CNY", description="货币")
    payment_method: str = Field(..., description="支付方式: alipay / wechat")


class OrderRead(BaseModel):
    id: int
    user_id: int
    order_no: str
    product_type: str
    product_id: str
    product_name: str
    amount: Decimal
    currency: str
    payment_method: Optional[str]
    payment_status: str
    payment_transaction_id: Optional[str]
    paid_at: Optional[datetime]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentResponse(BaseModel):
    order: OrderRead
    payment_url: Optional[str] = Field(None, description="支付URL（用于跳转支付）")
    payment_qr_code: Optional[str] = Field(None, description="支付二维码（用于扫码支付）")
    message: str = "订单创建成功"


class PaymentCallbackRequest(BaseModel):
    order_no: str
    transaction_id: str
    payment_status: str
    amount: Decimal
    callback_data: Optional[dict] = None


class SubscriptionRead(BaseModel):
    id: int
    user_id: int
    plan_type: str
    status: str
    started_at: datetime
    expires_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    auto_renew: bool
    next_billing_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubscriptionStatus(BaseModel):
    has_subscription: bool
    subscription: Optional[SubscriptionRead] = None
    is_premium: bool = Field(False, description="是否为高级会员")
    days_remaining: Optional[int] = Field(None, description="剩余天数")
