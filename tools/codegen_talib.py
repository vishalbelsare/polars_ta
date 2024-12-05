"""
Parse talib functions for polars Expressions

This version is more direct, without skip nan values, and without input and output checks

polars does not skip nan values as well. It should be processed by specific functions

本脚本主要功能是将talib封装成更适合表达式的版本

与另一版本的区别是这版本调用更直接，没有跳过空的操作，也没有输入与输出数量的判断工作
跳过空值等操作与polars样都不做，以后准备统一交给函数处理
"""
import talib as _talib
from talib import abstract as _abstract

from tools.prefix import save


def _codegen_func(name, input_names, parameters, output_names, doc):
    tpl11 = """
def {name}({aa}) -> Expr:  # {output_names}
    \"\"\"{doc}\"\"\"
    return {bb}.map_batches(lambda x1: batches_i1_o1(x1.to_numpy().astype(float), {cc}))
"""
    tpl12 = """
def {name}({aa}) -> Expr:  # {output_names}
    \"\"\"{doc}\"\"\"
    dtype = Struct([Field(f"column_{{i}}", Float64) for i in range({ee})])
    return {bb}.map_batches(lambda x1: batches_i1_o2(x1.to_numpy().astype(float), {cc}), return_dtype=dtype)
"""
    tpl21 = """
def {name}({aa}) -> Expr:  # {output_names}
    \"\"\"{doc}\"\"\"
    return struct([{bb}]).map_batches(lambda xx: batches_i2_o1([xx.struct[i].to_numpy().astype(float) for i in range({dd})], {cc}))
"""
    tpl22 = """
def {name}({aa}) -> Expr:  # {output_names}
    \"\"\"{doc}\"\"\"
    dtype = Struct([Field(f"column_{{i}}", Float64) for i in range({ee})])
    return struct([{bb}]).map_batches(lambda xx: batches_i2_o2([xx.struct[i].to_numpy().astype(float) for i in range({dd})], {cc}), return_dtype=dtype)
"""
    if len(output_names) > 42:
        extra_args = {'ret_idx': len(output_names) - 1}
    else:
        extra_args = {}
    a1 = [f'{name}: Expr' for name in input_names]
    a2 = [f'{k}: {type(v).__name__} = {v}' for k, v in parameters.items()]
    a3 = [f'{k}: {type(v).__name__} = {v}' for k, v in extra_args.items()]
    aa = ', '.join(a1 + a2 + a3)

    bb = ', '.join(input_names)

    c1 = [f'_ta.{name}']
    if len(parameters) > 0:
        c2 = [f'{k}' for k, v in parameters.items()]
    else:
        c2 = []

    c3 = [f'{k}={k}' for k, v in extra_args.items()]
    cc = ', '.join(c1 + c2 + c3)

    if len(input_names) == 1 and len(output_names) == 1:
        return tpl11.format(name=name, aa=aa, bb=bb, cc=cc, dd=len(input_names), ee=len(output_names), output_names=output_names, doc=doc)
    elif len(input_names) == 1 and len(output_names) > 1:
        return tpl12.format(name=name, aa=aa, bb=bb, cc=cc, dd=len(input_names), ee=len(output_names), output_names=output_names, doc=doc)
    elif len(input_names) > 1 and len(output_names) == 1:
        return tpl21.format(name=name, aa=aa, bb=bb, cc=cc, dd=len(input_names), ee=len(output_names), output_names=output_names, doc=doc)
    else:
        return tpl22.format(name=name, aa=aa, bb=bb, cc=cc, dd=len(input_names), ee=len(output_names), output_names=output_names, doc=doc)


def codegen():
    head_v2 = """# generated by codegen_talib.py
import talib as _ta
from polars import Expr, struct, Struct, Field, Float64

from polars_ta.utils.numba_ import batches_i1_o1, batches_i1_o2, batches_i2_o1, batches_i2_o2
"""

    txts = [head_v2]
    for i, func_name in enumerate(_talib.get_functions()):
        """talib遍历"""
        info = _abstract.Function(func_name).info

        name = info['name']
        input_names = []
        for in_names in info['input_names'].values():
            if isinstance(in_names, (list, tuple)):
                input_names.extend(list(in_names))
            else:
                input_names.append(in_names)
        parameters = info['parameters']
        output_names = info['output_names']
        txt = _codegen_func(name, input_names, parameters, output_names, getattr(_talib, name).__doc__)
        txts.append(txt)

    return txts


if __name__ == '__main__':
    txts = codegen()
    save(txts, module='polars_ta.talib', write=True)
