// MongoDB初始化脚本
// 创建数据库和基本集合结构

print('开始初始化NutriGuide PDF解析数据库...');

// 切换到目标数据库
db = db.getSiblingDB('nutriguide_pdf_parser');

// 创建解析结果集合
db.createCollection('parsing_results');
print('✅ 创建 parsing_results 集合');

// 创建批处理记录集合
db.createCollection('batch_records');
print('✅ 创建 batch_records 集合');

// 创建任务状态集合
db.createCollection('task_status');
print('✅ 创建 task_status 集合');

// 创建索引以提高查询性能
print('📊 创建索引...');

// parsing_results索引
db.parsing_results.createIndex({ "file_id": 1 }, { unique: true });
db.parsing_results.createIndex({ "status": 1 });
db.parsing_results.createIndex({ "created_at": -1 });
db.parsing_results.createIndex({ "parsing_type": 1 });
db.parsing_results.createIndex({ "quality_score": -1 });
print('✅ parsing_results 索引创建完成');

// batch_records索引
db.batch_records.createIndex({ "batch_id": 1 }, { unique: true });
db.batch_records.createIndex({ "created_at": -1 });
db.batch_records.createIndex({ "status": 1 });
print('✅ batch_records 索引创建完成');

// task_status索引
db.task_status.createIndex({ "task_id": 1 }, { unique: true });
db.task_status.createIndex({ "status": 1 });
db.task_status.createIndex({ "created_at": -1 });
print('✅ task_status 索引创建完成');

// 插入一些示例配置数据
print('📝 插入配置数据...');

// 创建配置集合
db.createCollection('config');

// 插入解析类型配置
db.config.insertOne({
    "_id": "parsing_types",
    "types": [
        {
            "key": "auto",
            "name": "自动识别",
            "description": "自动识别文档类型并选择合适的解析器"
        },
        {
            "key": "nutrition_label",
            "name": "营养标签",
            "description": "解析食品营养标签信息"
        },
        {
            "key": "recipe",
            "name": "食谱",
            "description": "解析食谱和制作方法"
        },
        {
            "key": "diet_guide",
            "name": "膳食指南",
            "description": "解析膳食指导文档"
        },
        {
            "key": "food",
            "name": "食品信息",
            "description": "解析一般食品信息"
        }
    ],
    "created_at": new Date()
});

// 插入营养成分标准配置
db.config.insertOne({
    "_id": "nutrition_standards",
    "nutrients": [
        {
            "key": "calories",
            "name": "热量",
            "unit": "kcal",
            "aliases": ["energy", "能量", "卡路里"]
        },
        {
            "key": "protein",
            "name": "蛋白质",
            "unit": "g",
            "aliases": ["蛋白"]
        },
        {
            "key": "fat",
            "name": "脂肪",
            "unit": "g",
            "aliases": ["总脂肪"]
        },
        {
            "key": "carbohydrates",
            "name": "碳水化合物",
            "unit": "g",
            "aliases": ["碳水", "糖类"]
        },
        {
            "key": "fiber",
            "name": "膳食纤维",
            "unit": "g",
            "aliases": ["纤维"]
        },
        {
            "key": "sugar",
            "name": "糖",
            "unit": "g",
            "aliases": ["添加糖", "总糖"]
        },
        {
            "key": "sodium",
            "name": "钠",
            "unit": "mg",
            "aliases": ["盐"]
        },
        {
            "key": "calcium",
            "name": "钙",
            "unit": "mg",
            "aliases": []
        },
        {
            "key": "iron",
            "name": "铁",
            "unit": "mg",
            "aliases": []
        },
        {
            "key": "vitamin_c",
            "name": "维生素C",
            "unit": "mg",
            "aliases": ["VC", "抗坏血酸"]
        },
        {
            "key": "vitamin_a",
            "name": "维生素A",
            "unit": "μg",
            "aliases": ["VA"]
        }
    ],
    "created_at": new Date()
});

print('✅ 配置数据插入完成');

// 创建一个测试用户（开发环境）
if (db.getName() === 'nutriguide_pdf_parser') {
    print('🔧 创建开发环境测试数据...');

    // 插入一条示例解析记录
    db.parsing_results.insertOne({
        "file_id": "example_001",
        "filename": "example_nutrition_label.pdf",
        "parsing_type": "nutrition_label",
        "status": "completed",
        "result": {
            "basic_info": {
                "filename": "example_nutrition_label.pdf",
                "file_size": 1024000,
                "page_count": 1
            },
            "extracted_data": {
                "type": "food",
                "food_info": {
                    "name": "示例牛奶",
                    "brand": "示例品牌"
                },
                "nutrition": {
                    "calories": { "value": 250, "unit": "kcal" },
                    "protein": { "value": 15, "unit": "g" },
                    "fat": { "value": 8, "unit": "g" },
                    "carbohydrates": { "value": 35, "unit": "g" }
                }
            },
            "quality_score": 85.5,
            "parsing_type": "nutrition_label",
            "status": "completed"
        },
        "progress": 100,
        "created_at": new Date(),
        "updated_at": new Date()
    });

    print('✅ 示例数据插入完成');
}

print('🎉 数据库初始化完成!');
print('📊 创建的集合:');
print('  - parsing_results: 解析结果');
print('  - batch_records: 批处理记录');
print('  - task_status: 任务状态');
print('  - config: 配置信息');
print('');
print('🔍 已创建的索引将提高查询性能');
print('📝 已插入基础配置数据'); 