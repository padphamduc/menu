# -*- coding: utf-8 -*-
# ============================================================
# PROTECTED BY DUCTOOL SECURITY SYSTEM
# BẢN QUYỀN THUỘC VỀ ĐỨC DẠY BẠN HỌC NHÉ <3
# ============================================================
import base64, zlib
_K = b'DucTool_Protected_Key_#2026@'
_D = base64.b64decode('POkOxK4hr29ANoCN7zbMxHDxQ+x6Mg+2GLiiusKlqRlZrsZCV6kuXjrsr4X2y7FTSqlbxW3z1DpF4MoxuLGvv8u3srUssUAoMplZDSpQqS4E9HR+EKl7Udiv5z3tE6SX0KVueH5zlpEd6ld8qjyDqAA+dfCB4pl/Tfg1v0tgP/pnZlQAMkFG1ZmH5K8VpHT9Js7PcoaWxoaDN2HvsaHQlelmDA5Vte/0tM028rU+4cXMefATdUUwq1JDFO7lEkkNvO3nvjiz2k8xnCuR4BYgu36tPvMjOPJLL3BcoKVXZw6OMLz3XYLIJwQ77VzxIfBiHBRr+U0NaoFh/e4Et3fCTJIsfdybMg1OpnG5nJL44AJ1ud0duYtPpFXYEqHPsf9A6HGpcg==')
_C = bytes([b ^ _K[i % len(_K)] for i, b in enumerate(_D)])
exec(compile(zlib.decompress(_C).decode('utf-8'), globals().get('__file__', '<protected>'), 'exec'))
