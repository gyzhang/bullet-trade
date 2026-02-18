from typing import Optional, Dict, Any
from .base import BaseFinanceAgent, Msg, agentscope_available


class RiskControllerAgent(BaseFinanceAgent):
    def __init__(
        self,
        name: str = "RiskController",
        model_config_name: str = "qwen-max",
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            **kwargs
        )
        self.role = "风险控制官"
        self.description = "评估投资风险并提供风险控制建议"
    
    def reply(self, x: Optional[Msg] = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供策略建议，我将评估风险",
                role="assistant"
            )
        
        if agentscope_available and self.model:
            risk_prompt = f"""
            作为专业的风险控制官，请评估以下投资策略的风险：
            
            {x.content}
            
            请提供详细的风险评估报告，包括以下部分：
            
            ## 一、风险识别
            - 市场风险（系统性风险）
            - 个股风险（非系统性风险）
            - 流动性风险
            - 仓位风险
            - 操作风险
            - 政策风险
            - 外部环境风险
            
            ## 二、风险量化评估
            - 风险等级（低/中/高）
            - 最大回撤预测
            - 波动率预测
            - 夏普比率分析
            - 贝塔系数分析
            
            ## 三、风险控制措施
            - 仓位管理建议
            - 止损策略优化
            - 止盈策略优化
            - 分散投资建议
            - 对冲方案
            
            ## 四、紧急情况应对
            - 市场暴跌应对
            - 个股黑天鹅事件
            - 流动性危机应对
            - 政策突变应对
            - 技术故障应对
            
            ## 五、风险监控体系
            - 监控指标设置
            - 预警机制
            - 定期风险评估
            - 风险报告制度
            
            ## 六、风险调整建议
            - 基于风险的仓位调整
            - 基于风险的策略调整
            - 基于风险的标的调整
            - 基于风险的时间周期调整
            
            ## 七、风险评估结论
            - 总体风险评级
            - 风险收益比分析
            - 适合的投资者类型
            - 最终风险控制建议
            
            请提供具体的数据支撑和详细的风险控制措施，确保策略能够在各种市场环境下稳健运行。
            """
            
            try:
                import asyncio
                
                # 使用辅助方法获取模型响应
                async def call_model():
                    return await self._get_model_response(risk_prompt)
                
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
                content="智能体功能不可用，请安装 agentscope 包以启用风险评估功能。",
                role="assistant"
            )
