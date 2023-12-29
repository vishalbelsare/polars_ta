from tools.prefix import codegen_import, save

lines = []
lines += codegen_import('polars_ta.tdx.arithmetic', include_modules=['polars_ta.wq.arithmetic'])
lines += codegen_import('polars_ta.tdx.choice')
lines += codegen_import('polars_ta.tdx.energy', include_parameter=['N', 'N1'])
lines += codegen_import('polars_ta.tdx.logical', include_func=['CROSS', 'LONGCROSS', 'EXISTR', 'LAST'], include_parameter=['N'])
lines += codegen_import('polars_ta.tdx.moving_average', include_parameter=['M1'])
lines += codegen_import('polars_ta.tdx.over_bought_over_sold', include_parameter=['N'])
lines += codegen_import('polars_ta.tdx.pressure_support', include_parameter=['N'])
lines += codegen_import('polars_ta.tdx.reference', include_modules=['polars_ta.ta.overlap', 'polars_ta.ta.volatility', 'polars_ta.wq.arithmetic', 'polars_ta.wq.time_serie'], include_func=['BARSLAST', 'BARSLASTCOUNT', 'BARSSINCE', 'DMA', 'SUM_0', 'TR'], include_parameter=['N', 'd', 'timeperiod'])
lines += codegen_import('polars_ta.tdx.statistic', include_modules=['polars_ta.wq.time_serie'], include_parameter=['timeperiod', 'd'])
lines += codegen_import('polars_ta.tdx.trend', include_parameter=['N'])
lines += codegen_import('polars_ta.tdx.volume', include_func=['OBV'], include_parameter=['N'])
save(lines, module='polars_ta.prefix.tdx', write=True)