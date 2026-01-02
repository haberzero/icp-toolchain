"""
测试 ibc_funcs.py 中的验证和工具函数

该脚本测试 MD5 计算、符号统计、标识符验证等基础功能
验证这些工具函数的正确性和稳定性
"""

import hashlib
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from libs.ibc_funcs import IbcFuncs
from typedef.ibc_data_types import (ClassMetadata, FileMetadata,
                                    FolderMetadata, FunctionMetadata,
                                    VariableMetadata)


def create_test_meta(meta_type: str, **kwargs):
    """创建测试用的元数据对象（兼容旧测试）"""
    if meta_type == "class":
        return ClassMetadata(
            type="class",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            normalized_name=kwargs.get("normalized_name", "")
        )
    elif meta_type == "func":
        return FunctionMetadata(
            type="func",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            parameters=kwargs.get("parameters", {}),
            normalized_name=kwargs.get("normalized_name", "")
        )
    elif meta_type == "var":
        return VariableMetadata(
            type="var",
            visibility=kwargs.get("visibility", "public"),
            description=kwargs.get("description", ""),
            scope=kwargs.get("scope", "unknown"),
            normalized_name=kwargs.get("normalized_name", "")
        )
    elif meta_type == "folder":
        return FolderMetadata(type="folder")
    elif meta_type == "file":
        return FileMetadata(type="file")
    else:
        # 对于unknown等非标准类型，返回None以保持兼容性
        return None


def test_md5_calculation():
    """测试 MD5 计算功能"""
    print("\n测试 md5_calculation 功能...")
    
    try:
        # 测试文本MD5
        text1 = "Hello World"
        md5_1 = IbcFuncs.calculate_text_md5(text1)
        expected_md5 = hashlib.md5(text1.encode('utf-8')).hexdigest()
        assert md5_1 == expected_md5, f"MD5计算错误: {md5_1} != {expected_md5}"
        
        # 测试中文文本
        text2 = "测试中文内容"
        md5_2 = IbcFuncs.calculate_text_md5(text2)
        assert len(md5_2) == 32, f"MD5长度错误: {len(md5_2)}"
        assert md5_2.isalnum(), "MD5应为字母数字组合"
        
        # 测试空字符串
        text3 = ""
        md5_3 = IbcFuncs.calculate_text_md5(text3)
        assert md5_3 == hashlib.md5(b'').hexdigest(), "空字符串MD5计算错误"
        
        # 测试相同内容产生相同MD5
        text4 = "相同内容"
        md5_4a = IbcFuncs.calculate_text_md5(text4)
        md5_4b = IbcFuncs.calculate_text_md5(text4)
        assert md5_4a == md5_4b, "相同内容应产生相同MD5"
        
        # 测试不同内容产生不同MD5
        text5 = "不同内容"
        md5_5 = IbcFuncs.calculate_text_md5(text5)
        assert md5_4a != md5_5, "不同内容应产生不同MD5"
        
        # 测试特殊字符
        text6 = "Special!@#$%^&*()_+-=[]{}|;':\",./<>?"
        md5_6 = IbcFuncs.calculate_text_md5(text6)
        assert len(md5_6) == 32, "包含特殊字符的文本应正常计算MD5"
        
        # 测试换行符和空格
        text7 = "Line1\nLine2\tTab\r\n"
        md5_7 = IbcFuncs.calculate_text_md5(text7)
        assert len(md5_7) == 32, "包含换行符和制表符的文本应正常计算MD5"
        
        print("  ✓ MD5计算功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_symbols_metadata_md5():
    """测试符号元数据 MD5 计算功能"""
    print("\n测试 symbols_metadata_md5 功能...")
    
    try:
        # 测试简单元数据
        metadata1 = {
            "module.ClassA": create_test_meta("class", normalized_name="ClassA")
        }
        md5_1 = IbcFuncs.calculate_symbols_metadata_md5(metadata1)
        assert len(md5_1) == 32, "MD5长度应为32"
        
        # 测试复杂元数据
        metadata2 = {
            "module.ClassA": create_test_meta("class", normalized_name="ClassA", description="测试类"),
            "module.ClassA.func1": create_test_meta("func", normalized_name="func1", parameters={"param1": "参数1"})
        }
        md5_2 = IbcFuncs.calculate_symbols_metadata_md5(metadata2)
        assert len(md5_2) == 32, "MD5长度应为32"
        
        # 测试相同元数据产生相同MD5
        md5_2b = IbcFuncs.calculate_symbols_metadata_md5(metadata2)
        assert md5_2 == md5_2b, "相同元数据应产生相同MD5"
        
        # 测试不同元数据产生不同MD5
        assert md5_1 != md5_2, "不同元数据应产生不同MD5"
        
        # 测试空元数据
        metadata3 = {}
        md5_3 = IbcFuncs.calculate_symbols_metadata_md5(metadata3)
        assert len(md5_3) == 32, "空元数据也应产生有效MD5"
        
        # 测试键顺序不影响MD5(因为使用了sort_keys)
        metadata4a = {
            "b": create_test_meta("class", normalized_name="B"),
            "a": create_test_meta("class", normalized_name="A")
        }
        metadata4b = {
            "a": create_test_meta("class", normalized_name="A"),
            "b": create_test_meta("class", normalized_name="B")
        }
        md5_4a = IbcFuncs.calculate_symbols_metadata_md5(metadata4a)
        md5_4b = IbcFuncs.calculate_symbols_metadata_md5(metadata4b)
        assert md5_4a == md5_4b, "键顺序不应影响MD5值"
        
        # 测试包含特殊字符的元数据
        metadata6 = {
            "module.特殊字符": create_test_meta("class", description="包含特殊!@#$%字符")
        }
        md5_6 = IbcFuncs.calculate_symbols_metadata_md5(metadata6)
        assert len(md5_6) == 32, "包含特殊字符的元数据应正常计算MD5"
        
        print("  ✓ 符号元数据MD5计算测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_count_symbols():
    """测试符号统计功能"""
    print("\n测试 count_symbols 功能...")
    
    try:
        # 测试空元数据
        metadata1 = {}
        count1 = IbcFuncs.count_symbols_in_metadata(metadata1)
        assert count1 == 0, f"空元数据符号数应为0，实际为{count1}"
        
        # 测试只有文件夹和文件的元数据
        metadata2 = {
            "src": create_test_meta("folder"),
            "src.main": create_test_meta("file")
        }
        count2 = IbcFuncs.count_symbols_in_metadata(metadata2)
        assert count2 == 0, f"只有folder/file节点时符号数应为0，实际为{count2}"
        
        # 测试包含类、函数、变量的元数据
        metadata3 = {
            "src": create_test_meta("folder"),
            "src.main": create_test_meta("file"),
            "src.main.ClassA": create_test_meta("class"),
            "src.main.ClassA.func1": create_test_meta("func"),
            "src.main.ClassA.func1.param1": create_test_meta("var"),
            "src.main.var1": create_test_meta("var")
        }
        count3 = IbcFuncs.count_symbols_in_metadata(metadata3)
        assert count3 == 4, f"符号数应为4(1 class + 1 func + 2 var)，实际为{count3}"
        
        # 测试混合类型
        metadata4 = {
            "a.ClassA": create_test_meta("class"),
            "a.ClassB": create_test_meta("class"),
            "a.func1": create_test_meta("func"),
            "a.func2": create_test_meta("func"),
            "a.var1": create_test_meta("var"),
            "b": create_test_meta("folder"),
            "c": create_test_meta("file"),
            "d.unknown": None  # 非标准类型不统计
        }
        # 过滤掉None值
        metadata4 = {k: v for k, v in metadata4.items() if v is not None}
        count4 = IbcFuncs.count_symbols_in_metadata(metadata4)
        assert count4 == 5, f"符号数应为5(2 class + 2 func + 1 var)，实际为{count4}"
        
        # 测试大量符号
        metadata5 = {}
        for i in range(100):
            metadata5[f"module.class{i}"] = create_test_meta("class")
        count5 = IbcFuncs.count_symbols_in_metadata(metadata5)
        assert count5 == 100, f"符号数应为100，实际为{count5}"
        
        # 测试只有class类型
        metadata6 = {
            "a.ClassA": create_test_meta("class"),
            "b.ClassB": create_test_meta("class")
        }
        count6 = IbcFuncs.count_symbols_in_metadata(metadata6)
        assert count6 == 2, f"只有class时符号数应为2，实际为{count6}"
        
        # 测试只有func类型
        metadata7 = {
            "a.func1": create_test_meta("func"),
            "b.func2": create_test_meta("func"),
            "c.func3": create_test_meta("func")
        }
        count7 = IbcFuncs.count_symbols_in_metadata(metadata7)
        assert count7 == 3, f"只有func时符号数应为3，实际为{count7}"
        
        # 测试只有var类型
        metadata8 = {
            "a.var1": create_test_meta("var"),
            "b.var2": create_test_meta("var")
        }
        count8 = IbcFuncs.count_symbols_in_metadata(metadata8)
        assert count8 == 2, f"只有var时符号数应为2，实际为{count8}"
        
        print("  ✓ 符号统计功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validate_identifier():
    """测试标识符验证功能"""
    print("\n测试 validate_identifier 功能...")
    
    try:
        # 有效标识符 - 基础测试
        assert IbcFuncs.validate_identifier("validName") == True, "validName应有效"
        assert IbcFuncs.validate_identifier("_private") == True, "_private应有效"
        assert IbcFuncs.validate_identifier("name123") == True, "name123应有效"
        assert IbcFuncs.validate_identifier("_name_123") == True, "_name_123应有效"
        assert IbcFuncs.validate_identifier("ClassName") == True, "ClassName应有效"
        assert IbcFuncs.validate_identifier("CONSTANT_VALUE") == True, "CONSTANT_VALUE应有效"
        
        # 有效标识符 - 边界情况
        assert IbcFuncs.validate_identifier("_") == True, "单个下划线应有效"
        assert IbcFuncs.validate_identifier("__") == True, "双下划线应有效"
        assert IbcFuncs.validate_identifier("___") == True, "三下划线应有效"
        assert IbcFuncs.validate_identifier("a") == True, "单个字母应有效"
        assert IbcFuncs.validate_identifier("A") == True, "单个大写字母应有效"
        assert IbcFuncs.validate_identifier("_1") == True, "_1应有效"
        assert IbcFuncs.validate_identifier("a1b2c3") == True, "字母数字混合应有效"
        assert IbcFuncs.validate_identifier("__init__") == True, "__init__应有效"
        assert IbcFuncs.validate_identifier("__name__") == True, "__name__应有效"
        
        # 有效标识符 - 长标识符
        long_name = "a" * 100
        assert IbcFuncs.validate_identifier(long_name) == True, "长标识符应有效"
        
        # 无效标识符 - 空或特殊字符开头
        assert IbcFuncs.validate_identifier("") == False, "空字符串应无效"
        assert IbcFuncs.validate_identifier("123start") == False, "数字开头应无效"
        assert IbcFuncs.validate_identifier("1") == False, "单个数字应无效"
        assert IbcFuncs.validate_identifier("123") == False, "纯数字应无效"
        
        # 无效标识符 - 包含特殊字符
        assert IbcFuncs.validate_identifier("name-with-dash") == False, "包含连字符应无效"
        assert IbcFuncs.validate_identifier("name with space") == False, "包含空格应无效"
        assert IbcFuncs.validate_identifier("name.dot") == False, "包含点号应无效"
        assert IbcFuncs.validate_identifier("name$dollar") == False, "包含美元符应无效"
        assert IbcFuncs.validate_identifier("name@at") == False, "包含@符号应无效"
        assert IbcFuncs.validate_identifier("name#hash") == False, "包含#号应无效"
        assert IbcFuncs.validate_identifier("name!exclaim") == False, "包含感叹号应无效"
        assert IbcFuncs.validate_identifier("name%percent") == False, "包含百分号应无效"
        assert IbcFuncs.validate_identifier("name^caret") == False, "包含^号应无效"
        assert IbcFuncs.validate_identifier("name&and") == False, "包含&号应无效"
        assert IbcFuncs.validate_identifier("name*star") == False, "包含*号应无效"
        assert IbcFuncs.validate_identifier("name(paren") == False, "包含(号应无效"
        assert IbcFuncs.validate_identifier("name)paren") == False, "包含)号应无效"
        assert IbcFuncs.validate_identifier("name+plus") == False, "包含+号应无效"
        assert IbcFuncs.validate_identifier("name=equal") == False, "包含=号应无效"
        assert IbcFuncs.validate_identifier("name[bracket") == False, "包含[号应无效"
        assert IbcFuncs.validate_identifier("name]bracket") == False, "包含]号应无效"
        assert IbcFuncs.validate_identifier("name{brace") == False, "包含{号应无效"
        assert IbcFuncs.validate_identifier("name}brace") == False, "包含}号应无效"
        assert IbcFuncs.validate_identifier("name|pipe") == False, "包含|号应无效"
        assert IbcFuncs.validate_identifier("name\\backslash") == False, "包含\\号应无效"
        assert IbcFuncs.validate_identifier("name:colon") == False, "包含:号应无效"
        assert IbcFuncs.validate_identifier("name;semicolon") == False, "包含;号应无效"
        assert IbcFuncs.validate_identifier("name'quote") == False, "包含'号应无效"
        assert IbcFuncs.validate_identifier('name"doublequote') == False, '包含"号应无效'
        assert IbcFuncs.validate_identifier("name<less") == False, "包含<号应无效"
        assert IbcFuncs.validate_identifier("name>greater") == False, "包含>号应无效"
        assert IbcFuncs.validate_identifier("name,comma") == False, "包含,号应无效"
        assert IbcFuncs.validate_identifier("name/slash") == False, "包含/号应无效"
        assert IbcFuncs.validate_identifier("name?question") == False, "包含?号应无效"
        
        # 无效标识符 - 非ASCII字符
        assert IbcFuncs.validate_identifier("中文名称") == False, "中文字符应无效"
        assert IbcFuncs.validate_identifier("日本語") == False, "日文字符应无效"
        assert IbcFuncs.validate_identifier("한글") == False, "韩文字符应无效"
        assert IbcFuncs.validate_identifier("Αλφα") == False, "希腊字符应无效"
        assert IbcFuncs.validate_identifier("Кириллица") == False, "西里尔字符应无效"
        assert IbcFuncs.validate_identifier("name中文") == False, "混合中英文应无效"
        
        # 无效标识符 - 空白字符
        assert IbcFuncs.validate_identifier(" ") == False, "单个空格应无效"
        assert IbcFuncs.validate_identifier("\t") == False, "制表符应无效"
        assert IbcFuncs.validate_identifier("\n") == False, "换行符应无效"
        assert IbcFuncs.validate_identifier("\r") == False, "回车符应无效"
        assert IbcFuncs.validate_identifier(" name") == False, "前导空格应无效"
        assert IbcFuncs.validate_identifier("name ") == False, "尾随空格应无效"
        
        print("  ✓ 标识符验证功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simplify_symbol_path():
    """测试符号路径简化功能"""
    print("\n测试 simplify_symbol_path 功能...")
    
    try:
        # 构造项目目录结构
        proj_root_dict = {
            "src": {
                "ball": {
                    "ball_entity": "file_content"
                },
                "physics": {
                    "gravity": "file_content",
                    "friction": "file_content"
                }
            }
        }
        
        # 测试简单路径
        path1 = "src.ball.ball_entity.BallEntity"
        result1 = IbcFuncs._simplify_symbol_path(path1, proj_root_dict)
        assert result1 == "ball_entity.BallEntity", f"预期'ball_entity.BallEntity'，实际'{result1}'"
        
        # 测试嵌套路径
        path2 = "src.physics.gravity.apply_gravity"
        result2 = IbcFuncs._simplify_symbol_path(path2, proj_root_dict)
        assert result2 == "gravity.apply_gravity", f"预期'gravity.apply_gravity'，实际'{result2}'"
        
        # 测试多级符号路径
        path3 = "src.ball.ball_entity.BallEntity.get_position.x"
        result3 = IbcFuncs._simplify_symbol_path(path3, proj_root_dict)
        assert result3 == "ball_entity.BallEntity.get_position.x", f"预期'ball_entity.BallEntity.get_position.x'，实际'{result3}'"
        
        # 测试找不到文件的情况（返回原路径）
        path4 = "unknown.module.symbol"
        result4 = IbcFuncs._simplify_symbol_path(path4, proj_root_dict)
        assert result4 == "unknown.module.symbol", f"未知路径应返回原路径，实际'{result4}'"
        
        # 测试只有文件名的路径
        path5 = "src.ball.ball_entity"
        result5 = IbcFuncs._simplify_symbol_path(path5, proj_root_dict)
        assert result5 == "ball_entity", f"预期'ball_entity'，实际'{result5}'"
        
        print("  ✓ 符号路径简化功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_build_available_symbol_list():
    """测试可用符号列表构建功能"""
    print("\n测试 build_available_symbol_list 功能...")
    
    try:
        # 构造项目目录结构
        proj_root_dict = {
            "src": {
                "ball": {
                    "ball_entity": "file_content"
                }
            }
        }
        
        # 构造符号元数据
        symbols_metadata = {
            "src": create_test_meta("folder"),
            "src.ball": create_test_meta("folder"),
            "src.ball.ball_entity": create_test_meta("file"),
            "src.ball.ball_entity.BallEntity": create_test_meta(
                "class",
                description="球体实体类"
            ),
            "src.ball.ball_entity.BallEntity.get_position": create_test_meta(
                "func",
                description="获取球体位置"
            ),
            "src.ball.ball_entity.BallEntity.velocity": create_test_meta(
                "var",
                description="球体速度"
            ),
            "src.ball.ball_entity.create_ball": create_test_meta("func")
        }
        
        # 构建可用符号列表
        symbol_list = IbcFuncs.build_available_symbol_list(symbols_metadata, proj_root_dict)
        
        # 验证结果
        assert len(symbol_list) == 4, f"预期4个符号，实际{len(symbol_list)}"
        assert "$ball_entity.BallEntity ：球体实体类" in symbol_list, "缺少BallEntity类"
        assert "$ball_entity.BallEntity.get_position ：获取球体位置" in symbol_list, "缺少get_position方法"
        assert "$ball_entity.BallEntity.velocity ：球体速度" in symbol_list, "缺少velocity变量"
        
        # 验证无描述的符号
        no_desc_found = False
        for item in symbol_list:
            if "create_ball" in item and "没有对外功能描述" in item:
                no_desc_found = True
                break
        assert no_desc_found, "应包含无描述的create_ball符号"
        
        # 验证不包含folder和file类型
        for item in symbol_list:
            assert "folder" not in item.lower(), "不应包含folder类型"
            assert "src.ball.ball_entity" not in item or "BallEntity" in item, "不应单独包含文件路径"
        
        print("  ✓ 可用符号列表构建功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_update_symbols_normalized_names():
    """测试批量更新符号规范化名称功能"""
    print("\n测试 update_symbols_normalized_names 功能...")
    
    try:
        # 创建测试元数据
        symbols_metadata = {
            "file.类名": ClassMetadata(
                type="class",
                description="测试类",
                visibility="public"
            ),
            "file.类名.方法名": FunctionMetadata(
                type="func",
                description="测试方法",
                visibility="public",
                parameters={"param1": "string"}
            ),
            "file.变量名": VariableMetadata(
                type="var",
                description="测试变量",
                visibility="public",
                scope="global"
            ),
            "folder1": FolderMetadata(type="folder"),
            "file1": FileMetadata(type="file")
        }
        
        # 构建规范化映射
        normalized_mapping = {
            "file.类名": "MyClass",
            "file.类名.方法名": "my_method",
            "file.变量名": "my_variable"
        }
        
        # 执行批量更新
        updated_count = IbcFuncs.update_symbols_normalized_names(symbols_metadata, normalized_mapping)
        
        # 验证更新数量
        assert updated_count == 3, f"应该更新 3 个符号，实际更新 {updated_count}"
        
        # 验证类元数据更新
        class_meta = symbols_metadata["file.类名"]
        assert isinstance(class_meta, ClassMetadata), "应该保持 ClassMetadata 类型"
        assert class_meta.normalized_name == "MyClass", f"类名应该更新为 MyClass，实际为 {class_meta.normalized_name}"
        assert class_meta.description == "测试类", "其他字段应该保持不变"
        
        # 验证函数元数据更新
        func_meta = symbols_metadata["file.类名.方法名"]
        assert isinstance(func_meta, FunctionMetadata), "应该保持 FunctionMetadata 类型"
        assert func_meta.normalized_name == "my_method", f"方法名应该更新为 my_method，实际为 {func_meta.normalized_name}"
        assert func_meta.parameters == {"param1": "string"}, "参数应该保持不变"
        
        # 验证变量元数据更新
        var_meta = symbols_metadata["file.变量名"]
        assert isinstance(var_meta, VariableMetadata), "应该保持 VariableMetadata 类型"
        assert var_meta.normalized_name == "my_variable", f"变量名应该更新为 my_variable，实际为 {var_meta.normalized_name}"
        assert var_meta.scope == "global", "作用域应该保持不变"
        
        # 验证文件夹和文件节点未被修改
        assert isinstance(symbols_metadata["folder1"], FolderMetadata), "FolderMetadata 不应被修改"
        assert isinstance(symbols_metadata["file1"], FileMetadata), "FileMetadata 不应被修改"
        
        # 测试部分更新
        symbols_metadata2 = {
            "file.symbol1": ClassMetadata(type="class"),
            "file.symbol2": FunctionMetadata(type="func")
        }
        normalized_mapping2 = {"file.symbol1": "Symbol1"}
        updated_count2 = IbcFuncs.update_symbols_normalized_names(symbols_metadata2, normalized_mapping2)
        assert updated_count2 == 1, f"应该只更新 1 个符号，实际更新 {updated_count2}"
        
        # 测试空映射
        symbols_metadata3 = {"file.test": ClassMetadata(type="class")}
        updated_count3 = IbcFuncs.update_symbols_normalized_names(symbols_metadata3, {})
        assert updated_count3 == 0, "空映射应该不更新任何符号"
        
        print("  ✓ 批量更新符号规范化名称功能测试通过")
        return True
        
    except Exception as e:
        print(f"  ✖ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试 ibc_funcs.py 中的验证和工具功能...")
    print("=" * 60)
    
    try:
        test_results = []
        
        # 测试MD5计算功能
        test_results.append(("MD5计算功能", test_md5_calculation()))
        
        test_results.append(("符号元数据MD5计算", test_symbols_metadata_md5()))
        
        test_results.append(("符号统计功能", test_count_symbols()))
        
        test_results.append(("标识符验证功能", test_validate_identifier()))
        
        test_results.append(("符号路径简化功能", test_simplify_symbol_path()))
        
        test_results.append(("批量更新符号规范化名称", test_update_symbols_normalized_names()))
        test_results.append(("可用符号列表构建", test_build_available_symbol_list()))
        
        print("\n" + "=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "✓ 通过" if result else "❌ 失败"
            print(f"{test_name:30} {status}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print("=" * 60)
            print("所有测试通过！✓")
            print("=" * 60)
            return True
        else:
            print(f"⚠️  有 {failed} 个测试失败")
            return False
            
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
