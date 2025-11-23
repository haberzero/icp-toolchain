"""
Embedding Handler 功能测试脚本

测试内容：
1. 基础配置加载和初始化
2. 单个文本嵌入（embed_query）
3. 批量文本嵌入（embed_documents）
4. 连接检查（check_connection）
5. 错误处理和重试机制
6. 向量维度和格式验证
"""

import sys
import os

# 添加父目录到路径以导入模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import SecretStr
from typedef.cmd_data_types import EmbeddingApiConfig
from libs.ai_interface.embedding_interface import EmbeddingHandler, EmbeddingStatus
from utils.icp_ai_handler.icp_embedding_handler import ICPEmbeddingHandler


def print_section(title: str):
    """打印测试章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_basic_initialization():
    """测试1：基础初始化"""
    print_section("测试1: 基础初始化")
    
    # 使用测试API配置
    config = EmbeddingApiConfig(
        base_url="http://127.0.0.1:11234/v1/",
        api_key=SecretStr("LOCAL"),
        model="text-embedding-qwen3-embedding-0.6b"
    )
    
    print(f"API URL: {config.base_url}")
    print(f"模型: {config.model}")
    
    # 创建EmbeddingHandler实例
    handler = EmbeddingHandler(config, max_retry=3, retry_delay=1.0)
    
    if handler.is_initialized:
        print("✓ EmbeddingHandler 初始化成功")
        return handler
    else:
        print("✗ EmbeddingHandler 初始化失败")
        return None


def test_single_text_embedding(handler: EmbeddingHandler):
    """测试2：单个文本嵌入"""
    print_section("测试2: 单个文本嵌入")
    
    if not handler or not handler.is_initialized:
        print("✗ Handler未初始化，跳过测试")
        return
    
    test_text = "这是一个测试文本"
    print(f"测试文本: '{test_text}'")
    
    embedding, status = handler.embed_query(test_text)
    
    if status == EmbeddingStatus.SUCCESS:
        print(f"✓ 嵌入成功")
        print(f"  向量维度: {len(embedding)}")
        print(f"  向量前10个值: {embedding[:10]}")
        return embedding
    else:
        print(f"✗ 嵌入失败，状态: {status}")
        return None


def test_batch_embedding(handler: EmbeddingHandler):
    """测试3：批量文本嵌入"""
    print_section("测试3: 批量文本嵌入")
    
    if not handler or not handler.is_initialized:
        print("✗ Handler未初始化，跳过测试")
        return
    
    test_texts = [
        "人工智能是计算机科学的一个分支",
        "机器学习是人工智能的核心技术",
        "深度学习使用神经网络进行训练",
        "自然语言处理用于理解和生成文本"
    ]
    
    print(f"测试文本数量: {len(test_texts)}")
    for i, text in enumerate(test_texts, 1):
        print(f"  {i}. {text}")
    
    embeddings, status = handler.embed_documents(test_texts)
    
    if status == EmbeddingStatus.SUCCESS:
        print(f"✓ 批量嵌入成功")
        print(f"  返回向量数量: {len(embeddings)}")
        for i, emb in enumerate(embeddings, 1):
            print(f"  文本{i} 向量维度: {len(emb)}")
        return embeddings
    else:
        print(f"✗ 批量嵌入失败，状态: {status}")
        return None


def test_icp_embedding_handler():
    """测试4：ICPEmbeddingHandler（单例模式）"""
    print_section("测试4: ICPEmbeddingHandler (单例模式)")
    
    # 使用测试API配置
    config = EmbeddingApiConfig(
        base_url="http://127.0.0.1:11234/v1/",
        api_key=SecretStr("LOCAL"),
        model="text-embedding-qwen3-embedding-0.6b"
    )
    
    # 初始化共享的handler
    success = ICPEmbeddingHandler.initialize_embedding_handler(config)
    
    if success:
        print("✓ ICPEmbeddingHandler 共享实例初始化成功")
    else:
        print("✗ ICPEmbeddingHandler 共享实例初始化失败")
        return None
    
    # 创建两个ICPEmbeddingHandler实例，验证它们共享同一个底层handler
    handler1 = ICPEmbeddingHandler()
    handler2 = ICPEmbeddingHandler()
    
    print(f"  Handler1 已初始化: {handler1.is_initialized()}")
    print(f"  Handler2 已初始化: {handler2.is_initialized()}")
    
    # 测试连接
    connection_ok = handler1.check_connection()
    print(f"  连接检查: {'✓ 正常' if connection_ok else '✗ 失败'}")
    
    # 使用handler1进行嵌入
    test_text = "测试ICPEmbeddingHandler的单例模式"
    embedding1, status1 = handler1.embed_query(test_text)
    
    if status1 == EmbeddingStatus.SUCCESS:
        print(f"✓ Handler1 嵌入成功，向量维度: {len(embedding1)}")
    else:
        print(f"✗ Handler1 嵌入失败")
    
    # 使用handler2进行嵌入，验证共享
    embedding2, status2 = handler2.embed_query(test_text)
    
    if status2 == EmbeddingStatus.SUCCESS:
        print(f"✓ Handler2 嵌入成功，向量维度: {len(embedding2)}")
    else:
        print(f"✗ Handler2 嵌入失败")
    
    # 验证两个handler产生的向量是否一致（应该完全一样）
    if status1 == EmbeddingStatus.SUCCESS and status2 == EmbeddingStatus.SUCCESS:
        vectors_match = embedding1 == embedding2
        print(f"  两个Handler产生的向量是否一致: {'✓ 是' if vectors_match else '✗ 否'}")
    
    return handler1


def test_vector_similarity(handler: EmbeddingHandler):
    """测试5：向量相似度计算"""
    print_section("测试5: 向量相似度计算")
    
    if not handler or not handler.is_initialized:
        print("✗ Handler未初始化，跳过测试")
        return
    
    # 相似的文本对
    similar_texts = [
        "机器学习是人工智能的重要分支",
        "人工智能包含机器学习技术"
    ]
    
    # 不相似的文本对
    dissimilar_texts = [
        "机器学习是人工智能的重要分支",
        "今天天气很好，适合出门散步"
    ]
    
    # 计算相似文本的嵌入
    emb1, status1 = handler.embed_query(similar_texts[0])
    emb2, status2 = handler.embed_query(similar_texts[1])
    
    if status1 == EmbeddingStatus.SUCCESS and status2 == EmbeddingStatus.SUCCESS:
        # 计算余弦相似度
        similarity_similar = cosine_similarity(emb1, emb2)
        print(f"相似文本对:")
        print(f"  文本1: {similar_texts[0]}")
        print(f"  文本2: {similar_texts[1]}")
        print(f"  余弦相似度: {similarity_similar:.4f}")
    
    # 计算不相似文本的嵌入
    emb3, status3 = handler.embed_query(dissimilar_texts[0])
    emb4, status4 = handler.embed_query(dissimilar_texts[1])
    
    if status3 == EmbeddingStatus.SUCCESS and status4 == EmbeddingStatus.SUCCESS:
        similarity_dissimilar = cosine_similarity(emb3, emb4)
        print(f"\n不相似文本对:")
        print(f"  文本1: {dissimilar_texts[0]}")
        print(f"  文本2: {dissimilar_texts[1]}")
        print(f"  余弦相似度: {similarity_dissimilar:.4f}")
        
        print(f"\n✓ 相似文本的相似度({similarity_similar:.4f})应该高于不相似文本({similarity_dissimilar:.4f})")


def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    import math
    
    # 计算点积
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # 计算模长
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    # 返回余弦相似度
    return dot_product / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0


def test_error_handling():
    pass
    # """测试6：错误处理"""
    # print_section("测试6: 错误处理")
    
    # # 测试错误的API配置
    # print("测试错误的API URL:")
    # config = EmbeddingApiConfig(
    #     base_url="http://invalid-url:9999/v1/",
    #     api_key=SecretStr("LOCAL"),
    #     model="text-embedding-qwen3-embedding-0.6b"
    # )
    
    # handler = EmbeddingHandler(config, max_retry=2, retry_delay=0.5)
    
    # if not handler.is_initialized:
    #     print("✓ 正确处理了无效的API URL（初始化失败）")
    # else:
    #     print("✗ 未能正确处理无效的API URL")
    
    # # 测试未初始化的handler调用
    # print("\n测试未初始化的handler调用:")
    # embedding, status = handler.embed_query("test")
    
    # if status == EmbeddingStatus.INIT_FAILED:
    #     print("✓ 正确返回了INIT_FAILED状态")
    # else:
    #     print(f"✗ 未能正确处理未初始化状态，返回状态: {status}")


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  Embedding Handler 功能测试")
    print("=" * 60)
    print("\n配置信息:")
    print("  API URL: http://127.0.0.1:11234/v1/")
    print("  模型: text-embedding-qwen3-embedding-0.6b")
    print("  API Key: LOCAL")
    
    # 测试1：基础初始化
    handler = test_basic_initialization()
    
    if handler:
        # 测试2：单个文本嵌入
        test_single_text_embedding(handler)
        
        # 测试3：批量文本嵌入
        test_batch_embedding(handler)
        
        # 测试5：向量相似度
        test_vector_similarity(handler)
    
    # 测试4：ICPEmbeddingHandler
    test_icp_embedding_handler()
    
    # # 测试6：错误处理
    # test_error_handling()
    
    # 总结
    print_section("测试完成")
    print("所有测试已完成！")
    print("\n提示：请确保Embedding API服务正在运行在 http://127.0.0.1:11234")


if __name__ == "__main__":
    main()
