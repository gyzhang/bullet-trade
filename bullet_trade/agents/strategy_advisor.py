from typing import Optional, Dict, Any
from .base import BaseFinanceAgent, Msg, agentscope_available


class StrategyAdvisorAgent(BaseFinanceAgent):
    def __init__(
        self,
        name: str = "StrategyAdvisor",
        model_config_name: str = "qwen-max",
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            **kwargs
        )
        self.role = "策略顾问"
        self.description = "基于市场分析提供投资策略建议"
    
    def reply(self, x: Optional[Msg] = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供市场分析结果，我将提供策略建议",
                role="assistant"
            )
        
        if agentscope_available and self.model:
            strategy_prompt = f"""
            作为专业的投资策略顾问，基于以下市场分析：
            
            {x.content}
            
            请提供详细的投资策略建议报告，包括以下部分：
            
            ## 一、总体策略定位
            - 策略风格（激进/稳健/保守）
            - 适应的市场环境
            - 预期收益目标
            - 风险承受能力要求
            
            ## 二、资产配置建议
            - 股票仓位建议
            - 行业配置比例
            - 板块轮动策略
            - 现金/其他资产配置
            
            ## 三、具体交易标的
            - 推荐个股及代码
            - 推荐理由（基本面/技术面）
            - 目标价格区间
            - 入场时机建议
            
            ## 四、交易执行策略
            - 建仓策略（分批/一次性）
            - 加仓策略
            - 减仓策略
            - 止盈止损设置
            
            ## 五、风险控制措施
            - 最大回撤控制
            - 仓位管理
            - 止损策略
            - 对冲方案
            
            ## 六、策略调整机制
            - 定期调整频率
            - 触发调整的条件
            - 紧急情况应对
            - 策略评估指标
            
            ## 七、执行时间表
            - 短期操作计划（1-3天）
            - 中期操作计划（1-2周）
            - 长期操作计划（1个月以上）
            
            请确保建议具有可操作性、针对性和风险意识，提供具体的数值和时间点。
            """
            
            try:
                import asyncio
                
                # 使用辅助方法获取模型响应
                async def call_model():
                    return await self._get_model_response(strategy_prompt)
                
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
                content="智能体功能不可用，请安装 agentscope 包以启用策略建议功能。",
                role="assistant"
            )
