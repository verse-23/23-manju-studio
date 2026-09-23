# 名牌台账与揭示时机

人物字段：`asset_id, entity_id, name_as_shown, identity_line, public_alias, hidden_identity, first_visible_episode, valid_from, valid_until, source_quote, source_paragraphs, placement, template_id, variant_of, status`。

同一角色从“路人”到“城主”是一个实体的不同展示状态；两人同名不能合并。伪装身份以当前叙事为准，不能因为读完后文就替观众提前揭底。职务是事实，名牌中的“天才、最强、第一”也需来源，不能当装饰词随意加。

角色对另一人的口头称呼不必然是正式名字。姓名不确定可以只用已知身份或保留待核对，不能擅自补全。匿名群演/保安甲等没有明确介绍需求时不制造几十张无用名牌。

人物副标题优先短而有信息：职位、组织、已揭示关系取其一或必要两项。原文一长串身份不强行全塞；显示简写与完整原文分栏，让用户能追溯删减。

场景字段：`asset_id, location_id, display_name, parent_location, alias, time_label, story_period, source_quote, episodes_used, introduction_trigger, template_id, status`。

“旧仓库/废弃工厂”是否同地需上下文支持，不凭相似字面合并。“医院—手术室”和“医院—走廊”可共享地点家族；只有观众需要区分时才分别上牌。日夜变化通常不是新地点资产；明确需要时出副标题变体。“三年前”“同一时间”等时空标签必须有剧情依据。

入点使用原文动作/台词或粗剪实码，不能凭段落号伪造时间码。名牌通常跟随首次有效亮相或地点建立后出现；悬念段先给表情或空间，再揭牌，防止名牌比剧情更早说出答案。

对文字长短、少见字、左右位置各选一条试渲染，再处理全量。台账中始终区分“待设计、待参考、已渲染、Alpha通过、人工视觉通过、编辑器导入通过”，不把其中一项当作全部。
