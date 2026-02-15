from jqdata import *
import pandas as pd
import numpy as np
import datetime

def initialize(context):
    # 设置基准
    set_benchmark('000300.XSHG')
    # 设置滑点和佣金（增强回测真实性）
    set_slippage(FixedSlippage(0.0002))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, 
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    
    # 待选股票池
    g.stocks = [
        '600036.XSHG',  # 招商银行
        '601318.XSHG',  # 中国平安
        '000858.XSHE',  # 五粮液
        '300017.XSHE',  # 网宿科技
        '300674.XSHE',  # 宇信科技
        '600268.XSHG',  # 国电南自
        '600900.XSHG'   # 长江电力
    ]
    
    # 策略参数
    g.ma_short = 5          # 短期均线
    g.ma_long = 20          # 长期均线
    g.vol_window = 20       # 波动率窗口
    g.max_position_ratio = 0.9  # 最大仓位比例
    g.min_position_ratio = 0.3  # 最小仓位比例
    g.stop_loss = -0.08     # 止损比例
    g.take_profit = 0.15    # 止盈比例
    g.cost_prices = {}      # 记录买入成本价
    g.entry_dates = {}      # 记录买入日期
    
    # 每日14:30执行策略
    run_daily(period, time='14:30')


def get_market_volatility(context, stocks):
    """计算市场波动率（年化）"""
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    all_returns = []
    for stock in stocks:
        try:
            # 获取股票价格数据
            prices = get_price(stock, start_date=start_date, end_date=end_date, 
                              frequency='daily', fields=['close'], skip_paused=True)
            if not prices.empty and len(prices) > 1:
                # 计算日收益率并收集
                returns = prices['close'].pct_change().dropna()
                all_returns.extend(returns.tolist())
        except Exception as e:
            log.warning(f"计算{stock}波动率失败: {str(e)}")
            continue
    
    # 计算年化波动率，数据不足时返回默认值
    if len(all_returns) > 10:
        return np.std(all_returns) * np.sqrt(250)
    return 0.25


def calculate_position_ratio(market_vol):
    """根据市场波动率动态调整仓位比例"""
    if market_vol <= 0.15:
        return g.max_position_ratio
    elif market_vol >= 0.35:
        return g.min_position_ratio
    else:
        # 线性插值计算仓位
        return g.max_position_ratio - (market_vol - 0.15) / 0.20 * (g.max_position_ratio - g.min_position_ratio)


def get_stock_score(context, stock):
    """计算股票评分（0-4分），评分越高越值得买入"""
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    try:
        # 获取价格数据（跳过停牌日）
        prices = get_price(stock, start_date=start_date, end_date=end_date, 
                          frequency='daily', fields=['close'], skip_paused=True)
        
        # 数据不足时返回0分
        if prices.empty or len(prices) < g.ma_long:
            return 0, None, None
        
        closes = prices['close']
        # 计算均线
        ma_short = closes.rolling(window=g.ma_short).mean().iloc[-1]
        ma_long = closes.rolling(window=g.ma_long).mean().iloc[-1]
        
        # 均线计算失败返回0分
        if pd.isna(ma_short) or pd.isna(ma_long):
            return 0, None, None
        
        # 评分规则（总分4分）
        score = 0
        
        # 短期均线上穿长期均线（2分）
        if ma_short > ma_long:
            score += 2
        
        # 5日动量为正（1分）
        if len(closes) >= 5:
            momentum = closes.iloc[-1] / closes.iloc[-5] - 1
            if momentum > 0:
                score += 1
        
        # 均线差值占比>2%（1分）
        trend_strength = (ma_short - ma_long) / ma_long
        if trend_strength > 0.02:
            score += 1
        
        # 调试日志：输出每个股票的评分细节
        log.debug(f"{stock} 评分: {score}, 5日均线: {ma_short:.2f}, 20日均线: {ma_long:.2f}")
        return score, ma_short, ma_long
        
    except Exception as e:
        log.warning(f"计算{stock}评分失败: {str(e)}")
        return 0, None, None


def check_stock_available(context, stock):
    """优化的股票有效性检查：兼容回测行情数据"""
    try:
        # 方式1：优先用get_price获取最新价格（更稳定）
        latest_price = get_price(stock, start_date=context.current_dt, end_date=context.current_dt, 
                                frequency='minute', fields=['close'], skip_paused=True)
        if not latest_price.empty and latest_price['close'].iloc[-1] > 0:
            return True, latest_price['close'].iloc[-1]
        
        # 方式2：备用方案用get_current_data
        current_data = get_current_data()
        if stock in current_data:
            data = current_data[stock]
            if not data.paused and data.last_price > 0:
                return True, data.last_price
        
        return False, 0.0
    except Exception as e:
        log.warning(f"检查{stock}有效性失败: {str(e)}")
        return False, 0.0


def period(context):
    """每日执行的核心策略逻辑"""
    portfolio = context.portfolio
    total_value = portfolio.total_value
    # 实时获取可用现金，避免本地变量失效
    available_cash = portfolio.available_cash
    
    # 1. 计算市场波动率和目标仓位
    market_vol = get_market_volatility(context, g.stocks)
    position_ratio = calculate_position_ratio(market_vol)
    log.info(f"市场波动率: {market_vol*100:.2f}%, 目标仓位: {position_ratio*100:.1f}%")
    
    # 2. 止损/止盈/趋势转弱卖出逻辑
    for stock in g.stocks:
        # 检查股票是否有效
        is_available, current_price = check_stock_available(context, stock)
        if not is_available:
            continue
        
        # 关键修改：先检查是否有实际持仓（避免访问空Position对象）
        has_position = stock in portfolio.positions and portfolio.positions[stock].total_amount > 0
        if not has_position:
            continue
        
        # 获取有效持仓对象
        position = portfolio.positions[stock]
        
        # 初始化成本价（首次持仓时记录）
        if stock not in g.cost_prices:
            g.cost_prices[stock] = position.avg_cost
        cost_price = g.cost_prices[stock]
        
        # 计算收益率
        pnl_ratio = (current_price - cost_price) / cost_price
        # 计算持仓天数
        holding_days = (context.current_dt.date() - g.entry_dates[stock]).days if stock in g.entry_dates else 0
        
        # 止损逻辑
        if pnl_ratio <= g.stop_loss:
            order_target(stock, 0)
            log.info(f"[止损] {stock}: 收益率 {pnl_ratio*100:.2f}%, 持仓 {holding_days} 天")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            continue
        
        # 止盈逻辑
        if pnl_ratio >= g.take_profit:
            order_target(stock, 0)
            log.info(f"[止盈] {stock}: 收益率 {pnl_ratio*100:.2f}%, 持仓 {holding_days} 天")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            continue
        
        # 趋势转弱卖出（仅计算一次评分）
        score, ma_short, ma_long = get_stock_score(context, stock)
        if score <= 0 and ma_short is not None and ma_long is not None and ma_short < ma_long:
            order_target(stock, 0)
            log.info(f"[趋势转弱] {stock}: 5日均线 {ma_short:.2f} < 20日均线 {ma_long:.2f}")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
    
    # 3. 买入逻辑（核心优化）
    # 预计算所有股票评分，避免重复调用
    stock_scores = []
    for stock in g.stocks:
        score, ma_short, ma_long = get_stock_score(context, stock)
        if score > 0:
            stock_scores.append((stock, score, ma_short, ma_long))
    
    # 按评分降序排序
    stock_scores.sort(key=lambda x: x[1], reverse=True)
    log.info(f"符合买入条件的股票数量: {len(stock_scores)}")
    
    # 计算目标持仓市值和当前持仓市值
    target_total_position = total_value * position_ratio
    current_total_position = 0
    
    # 安全计算当前持仓市值（避免访问空数据）
    current_data = get_current_data()
    for stock, pos in portfolio.positions.items():
        if stock in current_data and pos.total_amount > 0:
            price = current_data[stock].last_price if current_data[stock].last_price > 0 else 0
            current_total_position += pos.total_amount * price
    
    # 可买入的资金量
    available_for_buy = target_total_position - current_total_position
    log.info(f"目标持仓市值: {target_total_position:.2f}, 当前持仓市值: {current_total_position:.2f}, 可买入金额: {available_for_buy:.2f}")
    
    # 有可买入资金且有符合条件的股票时执行买入
    if available_for_buy > 1000 and stock_scores:
        # 最多买3只股票
        max_buy_count = 3
        buy_count = 0
        per_stock_value = available_for_buy / max_buy_count
        log.info(f"每只股票目标买入金额: {per_stock_value:.2f}")
        
        # 遍历所有符合条件的股票，直到买够3只或无可用股票
        for stock, score, ma_short, ma_long in stock_scores:
            if buy_count >= max_buy_count:
                break
            
            # 跳过已有持仓的股票
            if stock in portfolio.positions and portfolio.positions[stock].total_amount > 0:
                log.info(f"跳过已有持仓的股票: {stock}")
                continue
            
            # 优化的行情检查
            is_available, current_price = check_stock_available(context, stock)
            if not is_available:
                log.info(f"跳过无行情/停牌/价格异常的股票: {stock}")
                continue
            
            # 单次买入金额（预留5%现金应对滑点，且不超过可用现金）
            buy_value = min(per_stock_value, available_cash * 0.95)
            if buy_value < 1000:
                log.info(f"{stock} 买入金额不足，跳过: {buy_value:.2f}")
                continue
            
            log.info(f"{stock} 当前价格: {current_price:.2f}, 计划买入金额: {buy_value:.2f}")
            
            # 执行买入
            try:
                order_result = order_value(stock, buy_value)
                # 精准判断下单是否成功
                if order_result and order_result.status == OrderStatus.Completed:
                    log.info(f"[买入成功] {stock}: 金额 {buy_value:.2f}, 价格 {current_price:.2f}, 评分 {score}")
                    # 记录成本价和买入日期
                    g.cost_prices[stock] = current_price
                    g.entry_dates[stock] = context.current_dt.date()
                    buy_count += 1
                    # 实时更新可用现金
                    available_cash = portfolio.available_cash
                elif order_result:
                    log.warning(f"[买入委托] {stock}: 委托状态 {order_result.status}, 金额 {buy_value:.2f}")
                else:
                    log.warning(f"{stock} 下单失败，无委托返回")
            except Exception as e:
                log.error(f"{stock} 买入执行异常: {str(e)}")
        
        # 补充日志：提示买入结果
        if buy_count == 0:
            log.info(f"未买入任何股票：符合条件的{len(stock_scores)}只股票均无有效行情或金额不足")
        else:
            log.info(f"成功买入 {buy_count} 只股票，完成计划的 {buy_count}/{max_buy_count}")
    else:
        if available_for_buy <= 1000:
            log.info("可买入金额不足（<1000），跳过买入")
        if not stock_scores:
            log.info("无符合买入条件的股票，跳过买入")