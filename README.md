## 题库设置
在data\XXXXX.json中设置题目内容，文件名与index.json中对应即可，可参考默认案例。
```json
{
    "name":"题库名称",
    "problems":[
        {
            "content":"单选题干",
            "options":["选项A","选项B","选项C"],
            "analysis":"这题选C",
            "answer":3
        },
        {
            "content":"单选题干",
            "options":["选项A","选项B","选项C"],
            "analysis":"这题选C，同时支持选项引用，这里{{OPT:3}}选项是正确答案",
            "answer":3
        },
        {
            "content":"多选题干",
            "options":["选项A","选项B","选项C"],
            "analysis":"这题选AC",
            "answer":[1,3]
        },
        {
            "content":"多选题干",
            "options":["选项A","选项B","选项C"],
            "analysis":"这题选A",
            "answer":[1] // 数组表示是多选题
        },
        {
            "content":"判断题题干",
            "analysis":"解析也可以不写，直接去掉这个字段即可",
            "answer":true // 布尔类型表示是判断题
        },
        {
            "content":"填空题题干，早上好，{{ANS}}，晚上好。\n一二{{ANS}}四五",
            "answer":["中午好","三"] // 字符串数组表示是填空题
        },
        {
            "content":"简答题题干",
            "answer":"这里填入答案" // 字符串表示是简答题
        },
    ]
}
```