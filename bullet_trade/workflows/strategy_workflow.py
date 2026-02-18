from typing import List, Dict, Any
from agentscope.message import Msg
from agentscope.pipelines import SequentialPipeline
from ..agents import (
    DataAnalystAgent,
    StrategyAdvisorAgent,
    RiskControllerAgent,
    ExecutorAgent,
    ReporterAgent
)


class InvestmentWorkflow:
    def __init__(
        self,
        model_config_name: str = "qwen-max",
        enable_risk_control: bool = True,
        enable_report: bool = True
    ):
        self.data_analyst = DataAnalystAgent(model_config_name=model_config_name)
        self.strategy_advisor = StrategyAdvisorAgent(model_config_name=model_config_name)
        self.risk_controller = RiskControllerAgent(model_config_name=model_config_name) if enable_risk_control else None
        self.executor = ExecutorAgent(model_config_name=model_config_name)
        self.reporter = ReporterAgent(model_config_name=model_config_name) if enable_report else None
        
        self.enable_risk_control = enable_risk_control
        self.enable_report = enable_report
    
    def run(self, market_data: str) -> Dict[str, Any]:
        results = {}
        
        # 步骤1: 数据分析
        print("=" * 60)
        print("步骤1: 数据分析")
        print("=" * 60)
        analysis_msg = Msg(name="user", content=market_data, role="user")
        analysis_result = self.data_analyst.reply(analysis_msg)
        results["analysis"] = analysis_result.content
        print(f"\n{analysis_result.content}\n")
        
        # 步骤2: 策略建议
        print("=" * 60)
        print("步骤2: 策略建议")
        print("=" * 60)
        strategy_result = self.strategy_advisor.reply(analysis_result)
        results["strategy"] = strategy_result.content
        print(f"\n{strategy_result.content}\n")
        
        # 步骤3: 风险评估（可选）
        if self.enable_risk_control and self.risk_controller:
            print("=" * 60)
            print("步骤3: 风险评估")
            print("=" * 60)
            risk_result = self.risk_controller.reply(strategy_result)
            results["risk"] = risk_result.content
            print(f"\n{risk_result.content}\n")
            
            # 步骤4: 交易执行（基于风险评估）
            print("=" * 60)
            print("步骤4: 交易执行")
            print("=" * 60)
            execution_result = self.executor.reply(risk_result)
        else:
            # 步骤3: 交易执行（直接基于策略）
            print("=" * 60)
            print("步骤3: 交易执行")
            print("=" * 60)
            execution_result = self.executor.reply(strategy_result)
        
        results["execution"] = execution_result.content
        print(f"\n{execution_result.content}\n")
        
        # 步骤5: 生成报告（可选）
        if self.enable_report and self.reporter:
            print("=" * 60)
            print("步骤5: 生成报告")
            print("=" * 60)
            report_result = self.reporter.reply(execution_result)
            results["report"] = report_result.content
            print(f"\n{report_result.content}\n")
        
        return results
    
    def quick_analysis(self, stock_code: str, market_data: str) -> str:
        """快速分析模式：仅数据分析和策略建议"""
        analysis_msg = Msg(name="user", content=f"股票代码: {stock_code}\n\n{market_data}", role="user")
        analysis_result = self.data_analyst.reply(analysis_msg)
        strategy_result = self.strategy_advisor.reply(analysis_result)
        return strategy_result.content
