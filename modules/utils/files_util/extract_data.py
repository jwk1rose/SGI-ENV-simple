import json

# 定义源文件和目标文件名
source_file_path = 'all_0612.jsonl'
output_file_path = 'extracted_inputs_from_jsonl.json'

# 创建一个空列表，用于存储所有提取出的input对象
all_inputs = []

print(f"正在从 JSONL 文件 '{source_file_path}' 中逐行读取数据...")

try:
    # 打开并逐行读取.jsonl文件
    with open(source_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # 跳过空行
            line = line.strip()
            if not line:
                continue

            try:
                # 1. 将当前行（字符串）解析为Python字典
                mission = json.loads(line)

                # 2. 检查 'input' 键是否存在
                if 'input' in mission:
                    # 3. 如果存在，则将其值添加到我们的列表中
                    all_inputs.append(mission['input'])
                else:
                    print(f"警告：在其中一行中未找到 'input' 键。内容: {line}")

            except json.JSONDecodeError:
                print(f"警告：无法解析其中一行，已跳过。内容: {line}")

    print(f"数据提取完成，共找到 {len(all_inputs)} 条 'input' 数据。")
    print(f"正在将结果写入到 '{output_file_path}' 文件中...")

    # 将提取出的数据列表写入一个新的、标准的JSON文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(all_inputs[:100], f, indent=2, ensure_ascii=False)

    print("处理完成！新文件已成功创建。")

except FileNotFoundError:
    print(f"错误: 找不到源文件 '{source_file_path}'。")
except Exception as e:
    print(f"发生了未知错误: {e}")
