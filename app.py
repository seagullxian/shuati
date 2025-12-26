from flask import Flask, render_template, jsonify, request
import json
import os
import random
from datetime import datetime

app = Flask(__name__)

# 确保路径跨平台兼容，且绝对路径正确
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# 确保data目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


# 自动识别题目类型（根据你的数据格式调整）
def get_problem_type(problem):
    answer = problem.get('answer')

    if isinstance(answer, bool):
        return 'judge'
    elif isinstance(answer, int):
        return 'single'
    elif isinstance(answer, list):
        # 检查是否是填空题
        if answer and isinstance(answer[0], str):
            return 'fill'
        else:
            return 'multiple'
    elif isinstance(answer, str):
        return 'essay'
    else:
        return 'unknown'


# 格式化题目内容，处理{{ANS}}占位符
def format_question_content(problem):
    content = problem.get('content', '')
    answer = problem.get('answer', '')

    if problem.get('type') == 'fill':
        # 为填空题添加输入框占位符
        if isinstance(answer, list):
            for i in range(len(answer)):
                placeholder = f"__________"
                if '{{ANS}}' in content:
                    content = content.replace('{{ANS}}',
                                              f'<span class="fill-blank" data-index="{i}">{placeholder}</span>', 1)
                elif '____' in content:
                    content = content.replace('____', f'<span class="fill-blank" data-index="{i}">{placeholder}</span>',
                                              1)

    return content


# 加载所有题库列表
def load_bank_list():
    bank_list = []
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        return bank_list

    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            bank_id = filename[:-5]
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    bank_data = json.load(f)
                    bank_name = bank_data.get('name', bank_id)
                    problems = bank_data.get('problems', [])
                    problem_count = len(problems)
                    # 统计题型
                    type_count = {}
                    for p in problems:
                        t = get_problem_type(p)
                        type_count[t] = type_count.get(t, 0) + 1
                bank_list.append({
                    "id": bank_id,
                    "name": bank_name,
                    "count": problem_count,
                    "type_count": type_count,
                    "last_updated": datetime.now().strftime("%Y-%m-%d")
                })
            except Exception as e:
                print(f"加载题库{filename}失败：{e}")
                continue
    return bank_list


# 加载指定题库（带原始索引）
def load_bank_with_origin_idx(bank_id):
    file_path = os.path.join(DATA_DIR, f"{bank_id}.json")
    if not os.path.exists(file_path):
        print(f"题库文件不存在：{file_path}")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            bank_data = json.load(f)
            problems = bank_data.get('problems', [])
            # 为每个题目添加原始索引和格式化内容
            for idx, p in enumerate(problems):
                p['origin_idx'] = idx
                p['type'] = get_problem_type(p)
                p['formatted_content'] = format_question_content(p)
            bank_data['problems_with_origin'] = problems
        return bank_data
    except Exception as e:
        print(f"读取题库{bank_id}失败：{e}")
        return None


# 首页路由
@app.route('/')
def index():
    return render_template('index.html')


# 刷题页路由
@app.route('/practice')
def practice():
    return render_template('practice.html')


# 结果页路由
@app.route('/result')
def result():
    return render_template('result.html')


# 获取题库列表接口
@app.route('/api/banks', methods=['GET'])
def get_banks():
    try:
        bank_list = load_bank_list()
        return jsonify({
            "code": 200,
            "data": bank_list
        })
    except Exception as e:
        print(f"获取题库列表失败：{e}")
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)}"}), 500


# 获取题库题目接口
@app.route('/api/problems/<bank_id>', methods=['POST'])
def get_problems(bank_id):
    try:
        config = request.get_json()
        practice_mode = config.get('mode', 'all')
        target_type = config.get('type', 'single')
        shuffle = config.get('shuffle', False)

        bank = load_bank_with_origin_idx(bank_id)
        if not bank:
            return jsonify({"code": 400, "msg": f"题库【{bank_id}】不存在"}), 400

        problems = bank.get('problems_with_origin', [])

        # 按题型筛选
        if practice_mode == 'type':
            filtered_problems = []
            for p in problems:
                if p['type'] == target_type:
                    filtered_problems.append(p)
            problems = filtered_problems

        # 随机打乱
        if shuffle:
            random.shuffle(problems)

        return jsonify({"code": 200, "data": problems})
    except Exception as e:
        print(f"获取题目失败：{e}")
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)}"}), 500


# 校验答案接口
@app.route('/api/check_answer/<bank_id>', methods=['POST'])
def check_answer(bank_id):
    try:
        data = request.get_json()
        problem_origin_idx = data.get('problem_origin_idx')
        user_answer = data.get('user_answer')

        if problem_origin_idx is None:
            return jsonify({"code": 400, "msg": "缺少原始题目索引"}), 400

        # 重新加载题目数据
        bank = load_bank_with_origin_idx(bank_id)
        if not bank:
            return jsonify({"code": 400, "msg": f"题库【{bank_id}】不存在"}), 400

        problems = bank.get('problems_with_origin', [])
        if problem_origin_idx < 0 or problem_origin_idx >= len(problems):
            return jsonify({"code": 400, "msg": "原始题目索引错误"}), 400

        problem = problems[problem_origin_idx]
        correct_answer = problem['answer']
        analysis = problem.get('analysis', '无解析')
        question_type = problem['type']

        # 答案判断逻辑
        is_correct = False
        if question_type == 'judge':
            is_correct = (user_answer == correct_answer)
        elif question_type == 'single':
            is_correct = (user_answer == correct_answer)
        elif question_type == 'multiple':
            is_correct = (sorted(user_answer) == sorted(correct_answer))
        elif question_type == 'fill':
            is_correct = (user_answer == correct_answer)
        elif question_type == 'essay':
            is_correct = (user_answer.strip().lower() == correct_answer.strip().lower())

        # 解析替换{{OPT:X}}
        if '{{OPT:' in analysis and 'options' in problem:
            import re
            pattern = r'\{\{OPT:(\d+)\}\}'
            for match in re.findall(pattern, analysis):
                idx = int(match) - 1
                if 0 <= idx < len(problem['options']):
                    analysis = analysis.replace(f'{{{{OPT:{match}}}}}', problem['options'][idx])

        return jsonify({
            "code": 200,
            "data": {
                "is_correct": is_correct,
                "correct_answer": correct_answer,
                "analysis": analysis,
                "type": question_type
            }
        })
    except Exception as e:
        print(f"校验答案失败：{e}")
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)}"}), 500


# 获取练习结果接口
@app.route('/api/practice_result/<bank_id>', methods=['GET'])
def get_practice_result(bank_id):
    try:
        bank = load_bank_with_origin_idx(bank_id)
        if not bank:
            return jsonify({"code": 400, "msg": f"题库【{bank_id}】不存在"}), 400

        problems = bank.get('problems_with_origin', [])
        total_questions = len(problems)

        # 模拟答题结果
        correct_questions = int(total_questions * 0.6)
        accuracy = round((correct_questions / total_questions) * 100) if total_questions > 0 else 0

        # 题型统计
        question_stats = {
            "single": {"correct": int(correct_questions * 0.4), "wrong": int(total_questions * 0.1)},
            "multiple": {"correct": int(correct_questions * 0.3), "wrong": int(total_questions * 0.15)},
            "judge": {"correct": int(correct_questions * 0.2), "wrong": int(total_questions * 0.05)},
            "fill": {"correct": int(correct_questions * 0.1), "wrong": int(total_questions * 0.05)},
            "essay": {"correct": 0, "wrong": 0}
        }

        # 错题集（模拟数据）
        wrong_questions = []
        for i in range(min(3, total_questions)):
            problem = problems[i]
            wrong_questions.append({
                "question_number": i + 1,
                "type": problem['type'],
                "content": problem.get('content', ''),
                "user_answer": "错误答案示例",
                "correct_answer": problem.get('answer', ''),
                "analysis": problem.get('analysis', '无解析')
            })

        return jsonify({
            "code": 200,
            "data": {
                "total_questions": total_questions,
                "correct_questions": correct_questions,
                "accuracy": accuracy,
                "time_spent": 1560,
                "question_stats": question_stats,
                "knowledge_stats": {
                    "知识点A": {"correct": 5, "wrong": 2},
                    "知识点B": {"correct": 3, "wrong": 1},
                    "知识点C": {"correct": 4, "wrong": 3}
                },
                "wrong_questions": wrong_questions
            }
        })
    except Exception as e:
        print(f"获取练习结果失败：{e}")
        return jsonify({"code": 500, "msg": f"服务器错误：{str(e)}"}), 500


# 404错误处理
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
