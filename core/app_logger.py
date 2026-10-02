# -*- coding: utf-8 -*-
# ============================================================
# PROTECTED BY DUCTOOL SECURITY SYSTEM
# BẢN QUYỀN THUỘC VỀ ĐỨC DẠY BẠN HỌC NHÉ <3
# ============================================================
import base64, zlib
_K = b'DucTool_Protected_Key_#2026@'
_D = base64.b64decode('POneAtIBjxlAnJpg5lZ49e3782wJT4MxrAmoLYDEbMY9a+oe/LuOe+u5URMzYUDj00t0looYc9pPJ2ddH0AMypr5hzlXn2csrW4/S7vZ/6/pq1k+sm59FIDEcieC/SpM5fp9H0vt1msa81CulkIYg1Rgl7RL5U3OceonVZIY7mJsAW9EI3Ac4tZIzxHABUmZVPOvsrph4+mKg0F/kNMfmLe2WcsbKoMeunR9G/10guJTwTGKc6D7AsApeG6YcjSq1HWVOPmJOrApEE03Erlrj1zBOlkp+nnFnuXZHsAizA7kkXcoAb+oDNQgM9luyu3CwAaCO2hNXaFQJfgjKU9+e441bxoNdlKcZV5KY4Tl+u30tHkoo5I9EzqSJSAtxZVfMhMPfLp9abzhIb0BEyIUoyTWhkacSsRZpLG+hUi4XygMwNqMqIq+8y+cBrsrmVvf8P5hwUGCOX4Ol/nPFUJxO/NBfYQIgPwuHHGaynD1JHlbDRFAy9p+BEir6l3MlGbB2DvO0lzbCVIM6sR9ZbDGs4hHAfE2Gv+aZ6uspVefHjSrXGdJkQXZJ+viNlXllE7izmcbVK3g4jeVs8H/FVn2jp6sTjA6GJvaLB22Cb9vxsChUQRi/mAvPPeeWHdQUwzK7zKxCHZkuDRufaae2tv7BeSiMeZa7ZwK/WYYb/5mZvT1HKy/uKWKyvgJZTfgBWRf66lC+9o50LTdYgf0RARypGT/fTXYfV6FvW1Rx3nyW4EB5lQQELAsD0bfIY1TWWB7HVSaFRr30tSqQNmL3Zxhdz6hyvM4SnTQZ/VnTg+4xH2talul4XWo9joLcX3oMXsPedub5EwvZ4tF7LBbL41VPGJ3IiQp2dbRWt0Sz5wGu9R634dVUb+vyiHVVbILI+HuHhV6gzFz33hQ5XUCfrunuxc4D6O0lb6ep63VMiwNyIvSAx4ni/dlXLw2ldYPhCX1RB3/ovkRq7xh7Ww0LTyA3NCnCFvPhVaocRK4ZVyj0EPFcrWIzxOI09BroAgvva8vWp9NvtQb33oISqUrErdIiV2QXQmx80zp9zwpWomXBpfZrFhwXD8A1dReCjECu4hVs7gLSPwzJ5ETyfxk+rSsiLFGrMVAkAYBuhlMd4izVYGXf5jGZ/Y67+F0s9FbB7wcXm4FLNcoxG6jJp6nhZaDhud/QStLRzdoL5/jiB8eGizShDjlbyNYOZbs5fWpjNaoixFC88cCcegbL/goMExB3Ir2aXQXtd/kMRodkgapKJNc0ovD9p9x1mKz+L0SvDQ3xzuEyeFJGR4C0uvfajgf6/kpJ28x5yQjW+zK9JldCLaxHBATgi64Msy4+2VYVHx0oz1aKsEV6aY78P5gWqa3nzvOM5AmQrayZw==')
_C = bytes([b ^ _K[i % len(_K)] for i, b in enumerate(_D)])
exec(compile(zlib.decompress(_C).decode('utf-8'), globals().get('__file__', '<protected>'), 'exec'))
