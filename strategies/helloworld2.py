from jqdata import *

def initialize(context):
    set_benchmark('000300.XSHG')
    g.security = '600036.XSHG'
    g.ma_short = 5
    g.ma_long = 20
    g.position_ratio = 0.8
    g.stop_loss = -0.08
    g.take_profit = 0.15
    g.cost_price = None
    run_daily(period, time='14:30')


def period(context):
    security = g.security
    
    current_data = get_current_data()
    if security not in current_data:
        return
    
    data = current_data[security]
    current_price = data.last_price
    
    if current_price <= 0:
        return
    
    if data.paused:
        return
    
    end_date = context.current_dt
    start_date = end_date - datetime.timedelta(days=60)
    
    prices = get_price(security, start_date=start_date, end_date=end_date, 
                       frequency='daily', fields=['close'])
    
    if prices.empty or len(prices) < g.ma_long:
        return
    
    closes = prices['close']
    ma_short = closes.rolling(window=g.ma_short).mean().iloc[-1]
    ma_long = closes.rolling(window=g.ma_long).mean().iloc[-1]
    
    portfolio = context.portfolio
    position = portfolio.positions.get(security)
    total_value = portfolio.total_value
    cash = portfolio.available_cash
    
    if position and position.total_amount > 0:
        if g.cost_price is None:
            g.cost_price = position.avg_cost
        pnl_ratio = (current_price - g.cost_price) / g.cost_price
        
        if pnl_ratio <= g.stop_loss:
            order_target(security, 0)
            g.cost_price = None
            log.info(f"止损卖出: {security}, 收益率: {pnl_ratio*100:.2f}%")
            return
        
        if pnl_ratio >= g.take_profit:
            order_target(security, 0)
            g.cost_price = None
            log.info(f"止盈卖出: {security}, 收益率: {pnl_ratio*100:.2f}%")
            return
        
        if ma_short < ma_long:
            order_target(security, 0)
            g.cost_price = None
            log.info(f"趋势转弱卖出: {security}, 短期均线 {ma_short:.2f} < 长期均线 {ma_long:.2f}")
            return
    else:
        g.cost_price = None
    
    if ma_short > ma_long:
        if position and position.total_amount > 0:
            return
        
        target_value = total_value * g.position_ratio
        current_position_value = position.total_amount * current_price if position else 0
        buy_value = target_value - current_position_value
        
        if buy_value > cash * 0.95:
            buy_value = cash * 0.95
        
        if buy_value > 0:
            shares = int(buy_value / current_price / 100) * 100
            if shares >= 100:
                order(security, shares)
                g.cost_price = current_price
                log.info(f"买入: {security}, 数量: {shares}股, 均价: {current_price:.2f}, "
                        f"短期均线: {ma_short:.2f}, 长期均线: {ma_long:.2f}")
