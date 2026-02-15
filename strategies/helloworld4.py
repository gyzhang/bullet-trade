from jqdata import *
import pandas as pd
import numpy as np
import datetime


def initialize(context):
    set_benchmark('000300.XSHG')
    set_slippage(FixedSlippage(0.0002))
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, 
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    
    g.stocks = [
        '600036.XSHG',  # 招商银行
        '601318.XSHG',  # 中国平安
        '000858.XSHE',  # 五粮液
        '300017.XSHE',  # 网宿科技
        '300674.XSHE',  # 宇信科技
        '600268.XSHG',  # 国电南自
        '600900.XSHG'   # 长江电力
    ]
    
    g.market_index = '000300.XSHG'  # 大盘指数
    g.ma_short = 5
    g.ma_long = 20
    g.vol_window = 20
    g.max_position_ratio = 0.9
    g.min_position_ratio = 0.3
    g.stop_loss = -0.08
    g.take_profit = 0.15
    g.trailing_stop_ratio = 0.92  # 移动止损比例
    g.cost_prices = {}
    g.entry_dates = {}
    g.max_prices = {}  # 记录持仓期间最高价
    g.last_trade_dates = {}  # 记录每只股票最后交易日期
    
    run_daily(period, time='14:30')


def check_market_trend(context):
    """判断大盘趋势：牛市/熊市/中性"""
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    try:
        prices = get_price(g.market_index, start_date=start_date, end_date=end_date, 
                          frequency='daily', fields=['close'], skip_paused=True)
        
        if prices.empty or len(prices) < g.ma_long:
            return 'neutral'
        
        closes = prices['close']
        ma_short = closes.rolling(window=g.ma_short).mean().iloc[-1]
        ma_long = closes.rolling(window=g.ma_long).mean().iloc[-1]
        
        if pd.isna(ma_short) or pd.isna(ma_long):
            return 'neutral'
        
        if ma_short < ma_long * 0.98:
            return 'bear'
        elif ma_short > ma_long * 1.02:
            return 'bull'
        else:
            return 'neutral'
    except Exception as e:
        log.warning(f"判断大盘趋势失败: {str(e)}")
        return 'neutral'


def calculate_position_ratio(context, market_vol, market_trend):
    """根据市场波动率和大盘趋势动态调整仓位比例"""
    base_ratio = g.max_position_ratio
    
    if market_vol <= 0.15:
        base_ratio = g.max_position_ratio
    elif market_vol >= 0.35:
        base_ratio = g.min_position_ratio
    else:
        base_ratio = g.max_position_ratio - (market_vol - 0.15) / 0.20 * (g.max_position_ratio - g.min_position_ratio)
    
    if market_trend == 'bear':
        base_ratio *= 0.5
    elif market_trend == 'bull':
        base_ratio = min(base_ratio * 1.1, g.max_position_ratio)
    
    return base_ratio


def calculate_trailing_stop(context, stock, current_price):
    """计算移动止损价"""
    entry_date = g.entry_dates.get(stock)
    cost_price = g.cost_prices.get(stock)
    
    if entry_date and cost_price:
        holding_days = (context.current_dt.date() - entry_date).days
        max_price = g.max_prices.get(stock, cost_price)
        max_price = max(max_price, current_price)
        g.max_prices[stock] = max_price
        
        if holding_days > 5:
            return max(
                cost_price * (1 + g.stop_loss),
                max_price * g.trailing_stop_ratio
            )
    
    return cost_price * (1 + g.stop_loss)


def can_trade(context, stock):
    """检查是否可以交易（间隔过滤）"""
    last_trade_date = g.last_trade_dates.get(stock)
    if last_trade_date:
        days_since_trade = (context.current_dt.date() - last_trade_date).days
        if days_since_trade < 5:
            return False
    return True


def get_market_volatility(context, stocks):
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    all_returns = []
    for stock in stocks:
        try:
            prices = get_price(stock, start_date=start_date, end_date=end_date, 
                              frequency='daily', fields=['close'], skip_paused=True)
            if not prices.empty and len(prices) > 1:
                returns = prices['close'].pct_change().dropna()
                all_returns.extend(returns.tolist())
        except Exception as e:
            log.warning(f"计算{stock}波动率失败: {str(e)}")
            continue
    
    if len(all_returns) > 10:
        return np.std(all_returns) * np.sqrt(250)
    return 0.25


def get_stock_score(context, stock):
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    try:
        prices = get_price(stock, start_date=start_date, end_date=end_date, 
                          frequency='daily', fields=['close'], skip_paused=True)
        
        if prices.empty or len(prices) < g.ma_long:
            return 0, None, None
        
        closes = prices['close']
        ma_short = closes.rolling(window=g.ma_short).mean().iloc[-1]
        ma_long = closes.rolling(window=g.ma_long).mean().iloc[-1]
        
        if pd.isna(ma_short) or pd.isna(ma_long):
            return 0, None, None
        
        score = 0
        
        if ma_short > ma_long:
            score += 2
        
        if len(closes) >= 5:
            momentum = closes.iloc[-1] / closes.iloc[-5] - 1
            if momentum > 0:
                score += 1
        
        if len(closes) >= 20:
            momentum_20 = closes.iloc[-1] / closes.iloc[-20] - 1
            if momentum_20 > 0:
                score += 1
        
        trend_strength = (ma_short - ma_long) / ma_long
        if trend_strength > 0.02:
            score += 1
        
        log.debug(f"{stock} 评分: {score}, 5日均线: {ma_short:.2f}, 20日均线: {ma_long:.2f}")
        return score, ma_short, ma_long
        
    except Exception as e:
        log.warning(f"计算{stock}评分失败: {str(e)}")
        return 0, None, None


def check_stock_available(context, stock):
    try:
        latest_price = get_price(stock, start_date=context.current_dt, end_date=context.current_dt, 
                                frequency='minute', fields=['close'], skip_paused=True)
        if not latest_price.empty and latest_price['close'].iloc[-1] > 0:
            return True, latest_price['close'].iloc[-1]
        
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
    portfolio = context.portfolio
    total_value = portfolio.total_value
    available_cash = portfolio.available_cash
    
    market_trend = check_market_trend(context)
    market_vol = get_market_volatility(context, g.stocks)
    position_ratio = calculate_position_ratio(context, market_vol, market_trend)
    log.info(f"大盘趋势: {market_trend}, 市场波动率: {market_vol*100:.2f}%, 目标仓位: {position_ratio*100:.1f}%")
    
    for stock in g.stocks:
        is_available, current_price = check_stock_available(context, stock)
        if not is_available:
            continue
        
        has_position = stock in portfolio.positions and portfolio.positions[stock].total_amount > 0
        if not has_position:
            continue
        
        position = portfolio.positions[stock]
        
        if stock not in g.cost_prices:
            g.cost_prices[stock] = position.avg_cost
        cost_price = g.cost_prices[stock]
        
        pnl_ratio = (current_price - cost_price) / cost_price
        holding_days = (context.current_dt.date() - g.entry_dates[stock]).days if stock in g.entry_dates else 0
        
        trailing_stop = calculate_trailing_stop(context, stock, current_price)
        if current_price <= trailing_stop:
            order_target(stock, 0)
            log.info(f"[移动止损] {stock}: 当前价 {current_price:.2f} <= 止损价 {trailing_stop:.2f}, 收益率 {pnl_ratio*100:.2f}%, 持仓 {holding_days} 天")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            g.max_prices.pop(stock, None)
            g.last_trade_dates[stock] = context.current_dt.date()
            continue
        
        if pnl_ratio <= g.stop_loss:
            order_target(stock, 0)
            log.info(f"[止损] {stock}: 收益率 {pnl_ratio*100:.2f}%, 持仓 {holding_days} 天")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            g.max_prices.pop(stock, None)
            g.last_trade_dates[stock] = context.current_dt.date()
            continue
        
        if pnl_ratio >= g.take_profit:
            order_target(stock, 0)
            log.info(f"[止盈] {stock}: 收益率 {pnl_ratio*100:.2f}%, 持仓 {holding_days} 天")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            g.max_prices.pop(stock, None)
            g.last_trade_dates[stock] = context.current_dt.date()
            continue
        
        score, ma_short, ma_long = get_stock_score(context, stock)
        if score <= 0 and ma_short is not None and ma_long is not None and ma_short < ma_long:
            order_target(stock, 0)
            log.info(f"[趋势转弱] {stock}: 5日均线 {ma_short:.2f} < 20日均线 {ma_long:.2f}")
            g.cost_prices.pop(stock, None)
            g.entry_dates.pop(stock, None)
            g.max_prices.pop(stock, None)
            g.last_trade_dates[stock] = context.current_dt.date()
    
    stock_scores = []
    for stock in g.stocks:
        if not can_trade(context, stock):
            continue
        score, ma_short, ma_long = get_stock_score(context, stock)
        if score >= 2:
            stock_scores.append((stock, score, ma_short, ma_long))
    
    stock_scores.sort(key=lambda x: x[1], reverse=True)
    log.info(f"符合买入条件的股票数量: {len(stock_scores)}")
    
    target_total_position = total_value * position_ratio
    current_total_position = 0
    
    current_data = get_current_data()
    for stock, pos in portfolio.positions.items():
        if stock in current_data and pos.total_amount > 0:
            price = current_data[stock].last_price if current_data[stock].last_price > 0 else 0
            current_total_position += pos.total_amount * price
    
    available_for_buy = target_total_position - current_total_position
    log.info(f"目标持仓市值: {target_total_position:.2f}, 当前持仓市值: {current_total_position:.2f}, 可买入金额: {available_for_buy:.2f}")
    
    if available_for_buy > 1000 and stock_scores and market_trend != 'bear':
        max_buy_count = 3
        buy_count = 0
        per_stock_value = available_for_buy / max_buy_count
        log.info(f"每只股票目标买入金额: {per_stock_value:.2f}")
        
        for stock, score, ma_short, ma_long in stock_scores:
            if buy_count >= max_buy_count:
                break
            
            if stock in portfolio.positions and portfolio.positions[stock].total_amount > 0:
                log.info(f"跳过已有持仓的股票: {stock}")
                continue
            
            is_available, current_price = check_stock_available(context, stock)
            if not is_available:
                log.info(f"跳过无行情/停牌/价格异常的股票: {stock}")
                continue
            
            buy_value = min(per_stock_value, available_cash * 0.95)
            if buy_value < 1000:
                log.info(f"{stock} 买入金额不足，跳过: {buy_value:.2f}")
                continue
            
            log.info(f"{stock} 当前价格: {current_price:.2f}, 计划买入金额: {buy_value:.2f}")
            
            try:
                order_result = order_value(stock, buy_value)
                if order_result and order_result.status == OrderStatus.Completed:
                    log.info(f"[买入成功] {stock}: 金额 {buy_value:.2f}, 价格 {current_price:.2f}, 评分 {score}")
                    g.cost_prices[stock] = current_price
                    g.entry_dates[stock] = context.current_dt.date()
                    g.max_prices[stock] = current_price
                    g.last_trade_dates[stock] = context.current_dt.date()
                    buy_count += 1
                    available_cash = portfolio.available_cash
                elif order_result:
                    log.warning(f"[买入委托] {stock}: 委托状态 {order_result.status}, 金额 {buy_value:.2f}")
                else:
                    log.warning(f"{stock} 下单失败，无委托返回")
            except Exception as e:
                log.error(f"{stock} 买入执行异常: {str(e)}")
        
        if buy_count == 0:
            log.info(f"未买入任何股票：符合条件的{len(stock_scores)}只股票均无有效行情或金额不足")
        else:
            log.info(f"成功买入 {buy_count} 只股票，完成计划的 {buy_count}/{max_buy_count}")
    else:
        if available_for_buy <= 1000:
            log.info("可买入金额不足（<1000），跳过买入")
        if not stock_scores:
            log.info("无符合买入条件的股票（评分>=2），跳过买入")
        if market_trend == 'bear':
            log.info("大盘熊市，不进行买入操作")
