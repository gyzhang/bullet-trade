from typing import Optional, Dict, Any
from .base import BaseFinanceAgent, Msg, agentscope_available


class DataAnalystAgent(BaseFinanceAgent):
    def __init__(
        self,
        name: str = "DataAnalyst",
        model_config_name: str = "qwen-max",
        **kwargs
    ):
        super().__init__(
            name=name,
            model_config_name=model_config_name,
            **kwargs
        )
        self.role = "数据分析师"
        self.description = "分析市场数据、股票表现和技术指标"
    
    def reply(self, x: Optional[Msg] = None) -> Msg:
        if x is None:
            return Msg(
                name=self.name,
                content="请提供需要分析的市场数据或股票信息",
                role="assistant"
            )
        
        if agentscope_available and self.model:
            analysis_prompt = f"""
            作为专业的金融数据分析师，请分析以下市场数据：
            
            {x.content}
            
            请提供详细的市场分析报告，包括以下部分：
            
            ## 市场趋势分析
            - 当前市场所处阶段（牛市/熊市/震荡）
            - 近期市场走势特点
            - 主要影响因素分析
            
            ## 技术指标分析
            - 均线系统分析
            - 波动率分析
            - 市场情绪指标
            
            ## 板块分析
            - 领涨板块分析
            - 潜在机会板块
            - 风险板块提示
            
            ## 个股推荐
            - 明确推荐3-5只关注的个股及具体理由
            - 个股代码格式必须为：600000.XSHG 或 000000.XSHE
            - 每个推荐股票要有简洁的推荐理由
            
            ## 风险评估
            - 市场风险点
            - 政策风险
            - 外部环境风险
            
            ## 投资建议
            - 明确的仓位配置建议（百分比）
            - 行业配置建议
            - 具体的交易策略建议
            - 风险管理建议
            
            重要要求：
            1. 分析要专业、客观、简洁
            2. 推荐股票必须从提供的股票列表中选择
            3. 避免重复内容和冗长表述
            4. 直接给出明确的结论和建议
            """
            
            try:
                import asyncio
                
                # 使用辅助方法获取模型响应
                async def call_model():
                    return await self._get_model_response(analysis_prompt)
                
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
                content="智能体功能不可用，请安装 agentscope 包以启用智能分析功能。",
                role="assistant"
            )
