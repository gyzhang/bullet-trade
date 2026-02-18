from typing import Optional, Dict, Any
from .base import BaseFinanceAgent, Msg, agentscope_available


class ReporterAgent(BaseFinanceAgent):
    def __init__(
        self,
        name: str = "Reporter",
        model_config_name: str = "qwen-max",
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            **kwargs
        )
        self.role = "投资报告员"
        self.description = "生成投资分析报告和总结"
    
    def reply(self, x: Optional[Msg] = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供交易执行结果，我将生成投资报告",
                role="assistant"
            )
        
        if agentscope_available and self.model:
            report_prompt = f"""
            作为专业的投资报告员，请基于以下信息生成投资报告：
            
            {x.content}
            
            请生成完整的投资分析报告，包括：
            
            ## 一、市场概况
            - 市场整体走势
            - 重要事件回顾
            
            ## 二、投资决策
            - 决策依据
            - 交易标的
            - 仓位配置
            
            ## 三、风险评估
            - 主要风险点
            - 风险控制措施
            
            ## 四、执行情况
            - 成交情况
            - 执行偏差分析
            
            ## 五、投资建议
            - 后续操作建议
            - 需要关注的风险点
            
            ## 六、总结
            - 本次投资的核心逻辑
            - 经验教训
            
            请确保报告专业、客观、完整。
            """
            
            try:
                import asyncio
                
                # 使用辅助方法获取模型响应
                async def call_model():
                    return await self._get_model_response(report_prompt)
                
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
                content="智能体功能不可用，请安装 agentscope 包以启用报告生成功能。",
                role="assistant"
            )
