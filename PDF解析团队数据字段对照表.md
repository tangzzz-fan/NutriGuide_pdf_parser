# PDF解析团队数据字段对照表

## 快速参考指南

本文档为PDF解析团队提供快速的数据字段对照表，包含当前后端已实现的字段和建议新增的字段。

---

## 1. 食品数据字段 (Food)

### 1.1 当前已实现字段

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 食品名称 | `name` | String | ✓ | 中文名称，如"苹果" |
| 英文名称 | `nameEn` | String | - | 英文名称，如"Apple" |
| 描述 | `description` | String | - | 食品描述 |
| 主分类 | `category` | String | ✓ | 见分类枚举值 |
| 子分类 | `subcategories` | String[] | - | 如["红苹果","时令水果"] |
| 热量 | `nutrition.calories` | Number | ✓ | 每100g热量(kcal) |
| 蛋白质 | `nutrition.protein` | Number | ✓ | 每100g蛋白质(g) |
| 碳水化合物 | `nutrition.carbohydrates` | Number | ✓ | 每100g碳水(g) |
| 脂肪 | `nutrition.fat` | Number | ✓ | 每100g脂肪(g) |
| 膳食纤维 | `nutrition.fiber` | Number | - | 每100g纤维(g) |
| 糖分 | `nutrition.sugar` | Number | - | 每100g糖分(g) |
| 钠 | `nutrition.sodium` | Number | - | 每100g钠(mg) |
| 钾 | `nutrition.potassium` | Number | - | 每100g钾(mg) |
| 钙 | `nutrition.calcium` | Number | - | 每100g钙(mg) |
| 铁 | `nutrition.iron` | Number | - | 每100g铁(mg) |
| 维生素C | `nutrition.vitaminC` | Number | - | 每100g维C(mg) |
| 维生素A | `nutrition.vitaminA` | Number | - | 每100g维A(mcg) |
| 常用单位 | `commonUnits` | String[] | - | 如["个","片","杯"] |
| 过敏原 | `allergens` | String[] | - | 如["坚果","麸质"] |
| 饮食标签 | `dietaryTags` | String[] | - | 如["素食","无麸质"] |
| 条形码 | `barcode` | String | - | 包装食品条码 |
| 品牌 | `brand` | String | - | 品牌名称 |
| 图片URL | `imageUrl` | String | - | 食品图片链接 |
| 数据来源 | `dataSource` | String | - | manual/usda/api_import |

### 1.2 食品分类枚举值

| 英文值 | 中文含义 |
|--------|----------|
| `grains` | 谷物类 |
| `vegetables` | 蔬菜类 |
| `fruits` | 水果类 |
| `meat` | 肉类 |
| `poultry` | 禽肉类 |
| `seafood` | 海鲜类 |
| `dairy` | 乳制品 |
| `nuts` | 坚果类 |
| `legumes` | 豆类 |
| `beverages` | 饮料类 |
| `snacks` | 零食类 |
| `condiments` | 调料类 |
| `oils` | 油脂类 |
| `other` | 其他 |

---

## 2. 菜谱数据字段 (Recipe) - 建议新增

### 2.1 基本信息字段

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 菜谱ID | `recipeId` | ObjectId | ✓ | 唯一标识符 |
| 菜谱名称 | `recipeName` | String | ✓ | 中文名称 |
| 英文名称 | `recipeNameEn` | String | - | 英文名称 |
| 描述 | `description` | String | - | 菜谱描述 |
| 烹饪时间 | `cookingTime` | Number | - | 分钟数 |
| 难度等级 | `difficulty` | String | - | beginner/intermediate/advanced |
| 份数 | `servings` | Number | - | 可供几人食用 |
| 菜系 | `cuisine` | String | - | 如"sichuan","cantonese" |
| 适合餐次 | `mealType` | String[] | - | ["breakfast","lunch","dinner"] |
| 标签 | `tags` | String[] | - | 如["spicy","high_protein"] |
| 图片URL | `imageUrl` | String | - | 菜谱图片 |
| 来源文档 | `sourceDocument` | String | - | PDF文件名 |
| 解析状态 | `parsingStatus` | String | - | pending/completed/failed |
| 验证状态 | `verificationStatus` | String | - | pending/approved/rejected |

### 2.2 食材信息字段 (Recipe Ingredients)

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 菜谱ID | `recipeId` | ObjectId | ✓ | 关联菜谱 |
| 食品ID | `foodId` | ObjectId | - | 关联食品库 |
| 食材名称 | `ingredientName` | String | ✓ | 食材名称 |
| 用量 | `quantity` | Number | ✓ | 数量 |
| 单位 | `unit` | String | ✓ | 如"克","个","勺" |
| 是否主料 | `isMainIngredient` | Boolean | - | true/false |
| 处理方法 | `preparationMethod` | String | - | 如"切丁","切片" |

### 2.3 制作步骤字段 (Recipe Steps)

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 菜谱ID | `recipeId` | ObjectId | ✓ | 关联菜谱 |
| 步骤序号 | `stepNumber` | Number | ✓ | 1,2,3... |
| 步骤说明 | `instruction` | String | ✓ | 详细操作说明 |
| 耗时 | `duration` | Number | - | 分钟数 |
| 温度要求 | `temperature` | String | - | 如"中火","180度" |
| 步骤图片 | `imageUrl` | String | - | 步骤图片URL |

---

## 3. 用户相关字段

### 3.1 用户画像 (User Profile)

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 性别 | `gender` | String | ✓ | male/female/other |
| 年龄 | `age` | Number | ✓ | 10-120 |
| 身高 | `height` | Number | ✓ | 厘米 |
| 体重 | `weight` | Number | ✓ | 公斤 |
| 活动水平 | `activityLevel` | String | ✓ | 见活动水平枚举 |
| 健康状况 | `healthConditions` | String[] | - | 见健康状况枚举 |
| 过敏信息 | `allergies` | String[] | - | 如["花生","海鲜"] |
| 健康目标 | `mainGoal` | String | ✓ | 见健康目标枚举 |
| 目标体重 | `targetWeight` | Number | - | 公斤 |
| 目标时间 | `goalTimeline` | Number | - | 周数 |

### 3.2 用户偏好 (User Preferences)

| 中文名称 | 字段名 | 类型 | 必填 | 说明 |
|----------|--------|------|------|------|
| 口味偏好 | `tastePreferences` | String[] | - | 见口味枚举 |
| 地域习惯 | `regionalHabits` | String[] | - | 见菜系枚举 |
| 饮食限制 | `dietaryRestrictions` | String[] | - | 见饮食限制枚举 |
| 烹饪时间偏好 | `cookingTimePreference` | Number | - | 分钟数 |
| 烹饪技能 | `cookingSkill` | String | - | beginner/intermediate/advanced/expert |
| 预算水平 | `budgetPerMeal` | String | - | low/medium/high/premium |
| 喜爱食材 | `favoriteIngredients` | String[] | - | 如["鸡肉","西兰花"] |
| 不喜欢食材 | `dislikedIngredients` | String[] | - | 如["香菜","胡萝卜"] |

---

## 4. 常用枚举值速查

### 4.1 活动水平 (Activity Level)
- `sedentary` - 久坐
- `lightly_active` - 轻度活跃
- `moderately_active` - 中度活跃
- `very_active` - 高度活跃
- `extremely_active` - 极度活跃

### 4.2 健康目标 (Health Goal)
- `weight_loss` - 减重
- `weight_gain` - 增重
- `weight_maintain` - 维持体重
- `muscle_gain` - 增肌
- `improve_health` - 改善健康
- `manage_condition` - 管理疾病

### 4.3 口味偏好 (Taste Preference)
- `sweet` - 甜味
- `sour` - 酸味
- `bitter` - 苦味
- `spicy` - 辣味
- `salty` - 咸味
- `umami` - 鲜味
- `mild` - 清淡
- `rich` - 浓郁

### 4.4 地域菜系 (Regional Cuisine)
- `chinese_northern` - 中国北方菜
- `chinese_southern` - 中国南方菜
- `sichuan` - 川菜
- `cantonese` - 粤菜
- `hunan` - 湘菜
- `shandong` - 鲁菜
- `jiangsu` - 苏菜
- `western` - 西餐
- `japanese` - 日料
- `korean` - 韩料
- `thai` - 泰餐
- `mediterranean` - 地中海菜

### 4.5 饮食限制 (Dietary Restriction)
- `vegetarian` - 素食主义
- `vegan` - 纯素主义
- `pescatarian` - 鱼素主义
- `halal` - 清真
- `kosher` - 犹太洁食
- `gluten_free` - 无麸质
- `dairy_free` - 无乳制品
- `low_carb` - 低碳水
- `keto` - 生酮饮食
- `paleo` - 原始人饮食
- `no_pork` - 不吃猪肉
- `no_beef` - 不吃牛肉
- `no_seafood` - 不吃海鲜

---

## 5. PDF解析重点关注字段

### 5.1 食品解析优先级

**高优先级** (必须解析):
- 食品名称 (`name`)
- 主分类 (`category`)
- 基础营养信息 (`calories`, `protein`, `carbohydrates`, `fat`)

**中优先级** (建议解析):
- 详细营养信息 (`fiber`, `sugar`, `sodium`, `vitamins`)
- 子分类 (`subcategories`)
- 饮食标签 (`dietaryTags`)

**低优先级** (可选解析):
- 过敏原信息 (`allergens`)
- 常用单位 (`commonUnits`)
- 品牌信息 (`brand`)

### 5.2 菜谱解析优先级

**高优先级** (必须解析):
- 菜谱名称 (`recipeName`)
- 主要食材 (`ingredients`)
- 制作步骤 (`steps`)

**中优先级** (建议解析):
- 烹饪时间 (`cookingTime`)
- 难度等级 (`difficulty`)
- 菜系分类 (`cuisine`)

**低优先级** (可选解析):
- 营养师建议 (`nutritionistAdvice`)
- 适合人群 (`targetPopulation`)
- 注意事项 (`cautions`)

---

## 6. 数据质量要求

### 6.1 必填字段检查
- 确保所有标记为必填的字段都有值
- 数值字段不能为负数
- 字符串字段不能为空字符串

### 6.2 数据格式验证
- 营养数据应为合理范围内的数值
- 时间格式应为 HH:mm
- 枚举值必须在预定义列表中

### 6.3 数据一致性
- 食材名称应与食品库中的名称匹配
- 营养数据总和应符合逻辑
- 步骤序号应连续且唯一

---

## 7. 联系方式

如有疑问，请联系：
- **后端开发团队**: 数据结构相关问题
- **产品团队**: 业务逻辑相关问题
- **项目经理**: 优先级和时间安排

---

*本文档与《NutriGuide 后端数据字段说明文档》同步更新*
