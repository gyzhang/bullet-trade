from jqdata import *

def initialize(context):
    run_daily(period, time='14:30')
    g.security = '600036.XSHG'
    
def period(context):
    order(g.security, 500)