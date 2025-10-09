"""
与`WorldQuant Alpha101`的区别是添加了`cs_`前缀

由于截面与时序的使用方式不同，在自动化工具中如果不在名字上做区分就得手工注册，反而要麻烦些

"""
import polars_ols as pls
from polars import Expr, when, max_horizontal, UInt16, Int8, Utf8
from polars_ols import OLSKwargs

# In the original version, the function names are not prefixed with `cs_`,
# here we add it to prevent confusion
# 原版函数名都没有加`cs_`, 这里统一加一防止混淆


_ols_kwargs = OLSKwargs(null_policy='drop', solve_method='svd')


def cs_one_side(x: Expr, is_long: bool = True) -> Expr:
    """横截面上，将全部资产上调或下调，使得 Alpha 策略转为纯多头配置（当方向参数设为空头时则转为纯空头配置）

    Shifts all instruments up or down so that the Alpha becomes long-only or short-only
(if side = short), respectively.

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, -15, -7, 0, 20],
        'b': [None, 15, 7, 0, 20],
    }).with_columns(
        out1=cs_one_side(pl.col('a'), True),
        out2=cs_one_side(pl.col('a'), False),
        out3=cs_one_side(pl.col('b'), True),
        out4=cs_one_side(pl.col('b'), False),
    )
    shape: (5, 6)
    ┌──────┬──────┬──────┬──────┬──────┬──────┐
    │ a    ┆ b    ┆ out1 ┆ out2 ┆ out3 ┆ out4 │
    │ ---  ┆ ---  ┆ ---  ┆ ---  ┆ ---  ┆ ---  │
    │ i64  ┆ i64  ┆ i64  ┆ i64  ┆ i64  ┆ i64  │
    ╞══════╪══════╪══════╪══════╪══════╪══════╡
    │ null ┆ null ┆ null ┆ null ┆ null ┆ null │
    │ -15  ┆ 15   ┆ 0    ┆ -35  ┆ 15   ┆ -5   │
    │ -7   ┆ 7    ┆ 8    ┆ -27  ┆ 7    ┆ -13  │
    │ 0    ┆ 0    ┆ 15   ┆ -20  ┆ 0    ┆ -20  │
    │ 20   ┆ 20   ┆ 35   ┆ 0    ┆ 20   ┆ 0    │
    └──────┴──────┴──────┴──────┴──────┴──────┘
    ```

    """
    if is_long:
        return when(x.min() < 0).then(x - x.min()).otherwise(x)
    else:
        return when(x.max() > 0).then(x - x.max()).otherwise(x)


def cs_scale(x: Expr, scale_: float = 1, long_scale: float = 1, short_scale: float = 1) -> Expr:
    """横截面上，将输入数据进行比例调整

    此外，可通过向运算符添加额外参数，将多头头寸和空头头寸分别映射到独立的缩放比例上

    Scales input to booksize. We can also scale the long positions and short positions to separate scales by mentioning additional parameters to the operator.

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, -15, -7, 0, 20],
    }).with_columns(
        out1=cs_scale(pl.col('a'), 1),
        out2=cs_scale(pl.col('a'), 1, 2, 3),
    )
    shape: (5, 3)
    ┌──────┬───────────┬───────────┐
    │ a    ┆ out1      ┆ out2      │
    │ ---  ┆ ---       ┆ ---       │
    │ i64  ┆ f64       ┆ f64       │
    ╞══════╪═══════════╪═══════════╡
    │ null ┆ null      ┆ null      │
    │ -15  ┆ -0.357143 ┆ -2.045455 │
    │ -7   ┆ -0.166667 ┆ -0.954545 │
    │ 0    ┆ 0.0       ┆ 0.0       │
    │ 20   ┆ 0.47619   ┆ 2.0       │
    └──────┴───────────┴───────────┘
    ```

    References
    ----------
    https://platform.worldquantbrain.com/learn/operators/detailed-operator-descriptions#scale-x-scale1-longscale1-shortscale1

    """
    if long_scale != 1 or short_scale != 1:
        L = x.clip(lower_bound=0)  # 全正数
        S = x.clip(upper_bound=0)  # 全负数
        L = when(L.sum() == 0).then(0).otherwise(L / L.sum())
        S = when(S.sum() == 0).then(0).otherwise(S / S.sum())  # 负数/负数=正数
        return L * long_scale - S * short_scale
    else:
        return (x / x.abs().sum()).fill_nan(0) * scale_


def cs_scale_down(x: Expr, constant: int = 0) -> Expr:
    """横截面上，将每日数据按比例缩放至 [0,1] 区间，使得最小值映射为 0，最大值映射为 1，并通过减去常数偏移量调整最终结果

    Scales all values in each day proportionately between 0 and 1 such that minimum value maps to 0 and maximum value maps to 1.
    constant is the offset by which final result is subtracted

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, 15, 7, 0, 20],
    }).with_columns(
        out1=cs_scale_down(pl.col('a'), 0),
        out2=cs_scale_down(pl.col('a'), 1),
    )
    shape: (5, 3)
    ┌──────┬──────┬───────┐
    │ a    ┆ out1 ┆ out2  │
    │ ---  ┆ ---  ┆ ---   │
    │ i64  ┆ f64  ┆ f64   │
    ╞══════╪══════╪═══════╡
    │ null ┆ null ┆ null  │
    │ 15   ┆ 0.75 ┆ -0.25 │
    │ 7    ┆ 0.35 ┆ -0.65 │
    │ 0    ┆ 0.0  ┆ -1.0  │
    │ 20   ┆ 1.0  ┆ 0.0   │
    └──────┴──────┴───────┘
    ```

    References
    ----------
    https://platform.worldquantbrain.com/learn/operators/detailed-operator-descriptions#scale_downxconstant0

    """
    return ((x - x.min()) / (x.max() - x.min())).fill_nan(0) - constant


def cs_truncate(x: Expr, max_percent: float = 0.01) -> Expr:
    """横截面上，将所有 x 的取值截断至 maxPercent 指定的上限值，其中 maxPercent 需以十进制小数形式表示

    Operator truncates all values of x to maxPercent. Here, maxPercent is in decimal notation

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [3, 7, 20, 6],
    }).with_columns(
        out=cs_truncate(pl.col('a'), 0.5),
    )
    shape: (4, 2)
    ┌─────┬─────┐
    │ a   ┆ out │
    │ --- ┆ --- │
    │ i64 ┆ i64 │
    ╞═════╪═════╡
    │ 3   ┆ 3   │
    │ 7   ┆ 7   │
    │ 20  ┆ 18  │
    │ 6   ┆ 6   │
    └─────┴─────┘
    ```

    References
    ----------
    https://platform.worldquantbrain.com/learn/operators/detailed-operator-descriptions#truncatexmaxpercent001

    """
    return x.clip(upper_bound=x.sum() * max_percent)


def cs_fill_except_all_null(x: Expr, value: float = 0) -> Expr:
    """横截面上，全为`null`时，保持`null`，反之`null`填充为`value`

    Examples
    --------

    ```python
    df = pl.DataFrame({
        'a': [1, 2, None, 4, None],
        'b': [None, None, None, None, None],
    }).with_columns(
        A=cs_fill_except_all_null(pl.col('a')),
        B=cs_fill_except_all_null(pl.col('b')),
    )

    shape: (5, 4)
    ┌──────┬──────┬─────┬──────┐
    │ a    ┆ b    ┆ A   ┆ B    │
    │ ---  ┆ ---  ┆ --- ┆ ---  │
    │ i64  ┆ null ┆ i64 ┆ i32  │
    ╞══════╪══════╪═════╪══════╡
    │ 1    ┆ null ┆ 1   ┆ null │
    │ 2    ┆ null ┆ 2   ┆ null │
    │ null ┆ null ┆ 0   ┆ null │
    │ 4    ┆ null ┆ 4   ┆ null │
    │ null ┆ null ┆ 0   ┆ null │
    └──────┴──────┴─────┴──────┘
    ```

    Notes
    -----
    在权重矩阵中使用时。一定要保证所有股票都在，停牌不能被过滤了

    """
    return when(x.is_not_null().sum() == 0).then(x).otherwise(x.fill_null(value))


def cs_fill_mean(x: Expr) -> Expr:
    """横截面上，填充`null`为均值"""
    return x.fill_null(strategy='mean')


def cs_fill_max(x: Expr) -> Expr:
    """横截面上，填充`null`为最大值"""
    return x.fill_null(strategy='max')


def cs_fill_min(x: Expr) -> Expr:
    """横截面上，填充`null`为最小值"""
    return x.fill_null(strategy='min')


def cs_fill_null(x: Expr, value: float = 0) -> Expr:
    """横截面上，填充`null`为`value`"""
    return x.fill_null(value)


def cs_regression_neut(y: Expr, x: Expr) -> Expr:
    """横截面上，一元回归残差"""
    return pls.compute_least_squares(y, x, add_intercept=True, mode='residuals', ols_kwargs=_ols_kwargs)


def cs_regression_proj(y: Expr, x: Expr) -> Expr:
    """横截面上，一元回归预测"""
    return pls.compute_least_squares(y, x, add_intercept=True, mode='predictions', ols_kwargs=_ols_kwargs)


def cs_rank(x: Expr, pct: bool = True) -> Expr:
    """横截面排名

    Ranks the input among all the instruments and returns an equally distributed number between 0.0 and 1.0. For precise sort, use the rate as 0.

    Parameters
    ----------
    x
    pct
        * True: 排名百分比。范围：[0,1]
        * False: 排名。范围：[1,+inf)

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, 1, 1, 1, 2, 2, 3, 10],
    }).with_columns(
        out1=cs_rank(pl.col('a'), True),
        out2=cs_rank(pl.col('a'), False),
    )
    shape: (8, 3)
    ┌──────┬──────────┬──────┐
    │ a    ┆ out1     ┆ out2 │
    │ ---  ┆ ---      ┆ ---  │
    │ i64  ┆ f64      ┆ u32  │
    ╞══════╪══════════╪══════╡
    │ null ┆ null     ┆ null │
    │ 1    ┆ 0.0      ┆ 1    │
    │ 1    ┆ 0.0      ┆ 1    │
    │ 1    ┆ 0.0      ┆ 1    │
    │ 2    ┆ 0.333333 ┆ 2    │
    │ 2    ┆ 0.333333 ┆ 2    │
    │ 3    ┆ 0.666667 ┆ 3    │
    │ 10   ┆ 1.0      ┆ 4    │
    └──────┴──────────┴──────┘
    ```

    References
    ----------
    https://platform.worldquantbrain.com/learn/operators/detailed-operator-descriptions#rankx-rate2

    """
    if pct:
        # (x-x.min)/(x.max-x.min)
        r = x.rank(method='dense') - 1
        return r / max_horizontal(r.max(), 1)
    else:
        return x.rank(method='dense')


def cs_rank_if(condition: Expr, x: Expr, pct: bool = True) -> Expr:
    """横截面筛选排名。可实现动态票池

    Parameters
    ----------
    condition:Expr
        条件
    x:Expr
        因子
    pct:bool
        排名百分比。范围：[0,1]

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, 1, 1, 1, 2, 2, 3, 10],
        'b': [1, 2, 3, 4, 5, 6, None, 8],
    }).with_columns(
        out1=cs_rank_if(True, pl.col('a'), True),  # 与cs_rank等价
        out2=cs_rank_if(pl.col('b') > 3, -pl.col('a'), False),
    )

    shape: (8, 4)
    ┌──────┬──────┬──────────┬──────┐
    │ a    ┆ b    ┆ out1     ┆ out2 │
    │ ---  ┆ ---  ┆ ---      ┆ ---  │
    │ i64  ┆ i64  ┆ f64      ┆ u32  │
    ╞══════╪══════╪══════════╪══════╡
    │ null ┆ 1    ┆ null     ┆ null │
    │ 1    ┆ 2    ┆ 0.0      ┆ null │
    │ 1    ┆ 3    ┆ 0.0      ┆ null │
    │ 1    ┆ 4    ┆ 0.0      ┆ 3    │
    │ 2    ┆ 5    ┆ 0.333333 ┆ 2    │
    │ 2    ┆ 6    ┆ 0.333333 ┆ 2    │
    │ 3    ┆ null ┆ 0.666667 ┆ null │
    │ 10   ┆ 8    ┆ 1.0      ┆ 1    │
    └──────┴──────┴──────────┴──────┘
    ```

    Notes
    -----
    已经产生了新的None，尽量避免之后再进行ts_时序计算

    """
    return cs_rank(when(condition).then(x).otherwise(None), pct)


def _cs_qcut_rank(x: Expr, q: int = 10) -> Expr:
    """横截面上等频分箱

    Parameters
    ----------
    x
    q
        按频率分成`q`份

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, 1, 1, 1, 2, 2, 3, 10],
    }).with_columns(
        out1=cs_qcut(pl.col('a'), 10),
        out2=cs_qcut_rank(pl.col('a'), 10),
        out3=pl.col('a').map_batches(lambda x: pd.qcut(x, 10, labels=False, duplicates='drop')),
    )
    shape: (8, 4)
    ┌──────┬──────┬──────┬──────┐
    │ a    ┆ out1 ┆ out2 ┆ out3 │
    │ ---  ┆ ---  ┆ ---  ┆ ---  │
    │ i64  ┆ u16  ┆ u16  ┆ f64  │
    ╞══════╪══════╪══════╪══════╡
    │ null ┆ null ┆ null ┆ NaN  │
    │ 1    ┆ 0    ┆ 0    ┆ 0.0  │
    │ 1    ┆ 0    ┆ 0    ┆ 0.0  │
    │ 1    ┆ 0    ┆ 0    ┆ 0.0  │
    │ 2    ┆ 4    ┆ 3    ┆ 1.0  │
    │ 2    ┆ 4    ┆ 3    ┆ 1.0  │
    │ 3    ┆ 8    ┆ 6    ┆ 4.0  │
    │ 10   ┆ 9    ┆ 10   ┆ 5.0  │
    └──────┴──────┴──────┴──────┘
    ```

    Notes
    -----
    使用`rank`来实现`qcut`的效果

    """
    r = x.rank(method='dense') - 1
    return (r * q / max_horizontal(r.max(), 1)).cast(UInt16)


def cs_qcut(x: Expr, q: int = 10) -> Expr:
    """横截面上等频分箱

    Convert float values into indexes for user-specified buckets. Bucket is useful for creating group values, which can be passed to group operators as input.

    Parameters
    ----------
    x
    q
        按频率分成`q`份

    Examples
    --------

    ```python
    df = pl.DataFrame({
        'a': [None, 1, 1, 1, 2, 2, 3, 10],
    }).with_columns(
        out1=cs_qcut(pl.col('a'), 10),
        out2=pl.col('a').map_batches(lambda x: pd.qcut(x, 10, labels=False, duplicates='drop')),
    )
    shape: (8, 3)
    ┌──────┬──────┬──────┐
    │ a    ┆ out1 ┆ out2 │
    │ ---  ┆ ---  ┆ ---  │
    │ i64  ┆ u16  ┆ f64  │
    ╞══════╪══════╪══════╡
    │ null ┆ null ┆ NaN  │
    │ 1    ┆ 0    ┆ 0.0  │
    │ 1    ┆ 0    ┆ 0.0  │
    │ 1    ┆ 0    ┆ 0.0  │
    │ 2    ┆ 4    ┆ 1.0  │
    │ 2    ┆ 4    ┆ 1.0  │
    │ 3    ┆ 8    ┆ 4.0  │
    │ 10   ┆ 9    ┆ 5.0  │
    └──────┴──────┴──────┘

    ```

    Warnings
    --------
    目前与`pd.qcut`结果不同，等官方改进

    """
    # 实测直接to_physical()无法用于over,相当于with pl.StringCache():
    # return x.qcut(q, allow_duplicates=True).to_physical()

    return x.qcut(q, allow_duplicates=True, labels=[f'{i}' for i in range(q)]).cast(Utf8).cast(UInt16)


def cs_top_bottom(x: Expr, k: int = 10) -> Expr:
    """横截面上，排名。前K标记成-1，后K标记成1

    Examples
    --------
    ```python
    df = pl.DataFrame({
        'a': [None, 1, 2, 2, 2, 3, 5, 5, 5, 10],
    }).with_columns(
        out1=pl.col('a').rank(method='min'),
        out2=pl.col('a').rank(method='dense'),
        out3=cs_top_bottom(pl.col('a'), 2),
    )
    shape: (10, 4)
    ┌──────┬──────┬──────┬──────┐
    │ a    ┆ out1 ┆ out2 ┆ out3 │
    │ ---  ┆ ---  ┆ ---  ┆ ---  │
    │ i64  ┆ u32  ┆ u32  ┆ i8   │
    ╞══════╪══════╪══════╪══════╡
    │ null ┆ null ┆ null ┆ null │
    │ 1    ┆ 1    ┆ 1    ┆ -1   │
    │ 2    ┆ 2    ┆ 2    ┆ -1   │
    │ 2    ┆ 2    ┆ 2    ┆ -1   │
    │ 2    ┆ 2    ┆ 2    ┆ -1   │
    │ 3    ┆ 5    ┆ 3    ┆ 0    │
    │ 5    ┆ 6    ┆ 4    ┆ 1    │
    │ 5    ┆ 6    ┆ 4    ┆ 1    │
    │ 5    ┆ 6    ┆ 4    ┆ 1    │
    │ 10   ┆ 9    ┆ 5    ┆ 1    │
    └──────┴──────┴──────┴──────┘
    """

    # 值越小排第一，用来做空
    a = x.rank(method='dense')
    b = a.max() - a
    return (b < k).cast(Int8) - (a <= k).cast(Int8)
