from typing import Optional, Dict, Any
from .base import BaseFinanceAgent, Msg, agentscope_available


class ExecutorAgent(BaseFinanceAgent):
    def __init__(
        self,
        name: str = "Executor",
        model_config_name: str = "qwen-max",
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            **kwargs
        )
        self.role = "交易执行员"
        self.description = "将策略建议转化为具体的交易指令"
    
    def reply(self, x: Optional[Msg] = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供经过风险评估的策略，我将生成交易指令",
                role="assistant"
            )
        
        if agentscope_available and self.model:
            execution_prompt = f"""
            作为专业的交易执行员，请将以下策略转化为具体的交易指令：
            
            {x.content}
            
            请生成详细的交易计划：
            1. 具体的买入/卖出指令
               - 股票代码
               - 交易方向（买入/卖出）
               - 目标价格区间
               - 建议仓位
               - 交易时间窗口
            
            2. 订单执行策略
               - 市价单还是限价单
               - 分批建仓还是一次性建仓
               - 订单有效期
            
            3. 执行监控要点
               - 成交价格监控
               - 成交量监控
               - 异常情况处理
            
            请确保交易指令清晰、可执行。
            """
            
            try:
                import asyncio
                
                # 使用辅助方法获取模型响应
                async def call_model():
                    return await self._get_model_response(execution_prompt)
                
                content = asyncio.run(call_model())
                
                return Msg(
                    name=self.name,
                    content=content,
                    role="assistant"
                )
            except Exception as e:
                return Msg(
                    name=self.name,
                    content=f"模型调用失败: {str(e)}",
                    role="assistant"
                )
        else:
            # 如果 agentscope 不可用或模型未初始化，返回模拟响应
            return Msg(
                name=self.name,
                content="智能体功能不可用，请安装 agentscope 包以启用交易执行功能。",
                role="assistant"
            )
