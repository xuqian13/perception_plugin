"""
社交网络感知模块
分析用户关系图谱、群组角色、社交影响力等
"""

import time
from typing import Dict, Optional, Any, List, Set, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict, Counter
from src.common.logger import get_logger

logger = get_logger("social_network_perception")


@dataclass
class UserRelationship:
    """用户关系数据"""

    target_user_id: str
    target_nickname: str = ""
    interaction_count: int = 0  # 互动次数
    mention_count: int = 0  # 提及次数
    reply_count: int = 0  # 回复次数
    relationship_strength: float = 0.0  # 关系强度 0.0-1.0
    last_interaction_time: float = 0.0


@dataclass
class SocialNetworkStatus:
    """社交网络状态数据类"""

    chat_id: str = ""
    chat_name: str = ""

    # 用户角色
    user_roles: Dict[str, str] = None  # {user_id: role}
    # role可以是: "leader"(意见领袖), "active"(活跃分子), "regular"(普通成员), "lurker"(潜水者), "newcomer"(新人)

    # 关系图谱
    interaction_matrix: Dict[str, Dict[str, int]] = None  # {user_id: {target_id: count}}
    strong_relationships: List[Tuple[str, str, float]] = None  # [(user1, user2, strength)]

    # 社交影响力
    influence_scores: Dict[str, float] = None  # {user_id: influence_score}
    top_influencers: List[str] = None  # 影响力TOP用户

    # 小团体检测
    cliques: List[Set[str]] = None  # 小团体列表
    has_cliques: bool = False

    # 群组统计
    total_users: int = 0
    active_users: int = 0  # 活跃用户数（最近有发言）
    lurker_ratio: float = 0.0  # 潜水比例

    # 互动模式
    avg_interactions_per_user: float = 0.0
    interaction_diversity: float = 0.0  # 互动多样性（用户间互动的均匀程度）

    # 时间戳
    timestamp: float = 0.0

    def __post_init__(self):
        if self.user_roles is None:
            self.user_roles = {}
        if self.interaction_matrix is None:
            self.interaction_matrix = {}
        if self.strong_relationships is None:
            self.strong_relationships = []
        if self.influence_scores is None:
            self.influence_scores = {}
        if self.top_influencers is None:
            self.top_influencers = []
        if self.cliques is None:
            self.cliques = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换Set为List以便序列化
        data["cliques"] = [list(c) for c in self.cliques]
        return data

    def get_human_readable_summary(self) -> str:
        """获取人类可读的社交网络摘要"""
        parts = []

        # 群组规模
        parts.append(f"群组有{self.total_users}人，{self.active_users}人活跃")

        # 潜水比例
        if self.lurker_ratio > 0:
            parts.append(f"{self.lurker_ratio*100:.0f}%的人潜水")

        # 意见领袖
        leaders = [uid for uid, role in self.user_roles.items() if role == "leader"]
        if leaders:
            parts.append(f"有{len(leaders)}位意见领袖")

        # 小团体
        if self.has_cliques:
            parts.append(f"检测到{len(self.cliques)}个小团体")

        return "，".join(parts)


class SocialNetworkPerception:
    """社交网络感知器"""

    def __init__(self, interaction_threshold_days: int = 7):
        """
        初始化社交网络感知器

        Args:
            interaction_threshold_days: 互动统计时间窗口（天）
        """
        self.interaction_threshold_days = interaction_threshold_days

        # 存储互动记录
        # {chat_id: {user_id: [(target_id, timestamp, interaction_type)]}}
        self.interactions: Dict[str, Dict[str, List[Tuple[str, float, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # 用户在各群组的消息数
        # {chat_id: {user_id: message_count}}
        self.user_activity: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        logger.info(f"社交网络感知模块初始化完成，互动窗口: {interaction_threshold_days}天")

    def record_interaction(
        self,
        chat_id: str,
        user_id: str,
        target_user_id: Optional[str] = None,
        interaction_type: str = "message",
        timestamp: Optional[float] = None,
    ):
        """
        记录用户互动

        Args:
            chat_id: 聊天ID
            user_id: 用户ID
            target_user_id: 目标用户ID（提及、回复等）
            interaction_type: 互动类型 "message" | "mention" | "reply"
            timestamp: 时间戳
        """
        if timestamp is None:
            timestamp = time.time()

        # 记录活跃度
        self.user_activity[chat_id][user_id] += 1

        # 记录互动
        if target_user_id:
            self.interactions[chat_id][user_id].append((target_user_id, timestamp, interaction_type))

        # 清理过期数据
        self._cleanup_old_interactions(chat_id)

    def _cleanup_old_interactions(self, chat_id: str):
        """清理过期的互动记录"""
        cutoff_time = time.time() - (self.interaction_threshold_days * 86400)

        if chat_id in self.interactions:
            for user_id in list(self.interactions[chat_id].keys()):
                self.interactions[chat_id][user_id] = [
                    (target, ts, itype)
                    for target, ts, itype in self.interactions[chat_id][user_id]
                    if ts >= cutoff_time
                ]

    def _build_interaction_matrix(
        self, chat_id: str
    ) -> Dict[str, Dict[str, int]]:
        """构建互动矩阵"""
        matrix = defaultdict(lambda: defaultdict(int))

        if chat_id in self.interactions:
            for user_id, interactions in self.interactions[chat_id].items():
                for target_id, timestamp, itype in interactions:
                    matrix[user_id][target_id] += 1

        return dict(matrix)

    def _classify_user_role(
        self,
        user_id: str,
        message_count: int,
        total_messages: int,
        interaction_count: int,
        avg_interaction: float,
    ) -> str:
        """
        分类用户角色

        Args:
            user_id: 用户ID
            message_count: 用户消息数
            total_messages: 总消息数
            interaction_count: 用户互动数
            avg_interaction: 平均互动数

        Returns:
            角色标签
        """
        if message_count == 0:
            return "lurker"

        message_ratio = message_count / max(1, total_messages)

        # 意见领袖：发言多且互动多
        if message_ratio > 0.15 and interaction_count > avg_interaction * 1.5:
            return "leader"

        # 活跃分子：发言多
        elif message_ratio > 0.10 or message_count > 50:
            return "active"

        # 新人：发言很少
        elif message_count < 5:
            return "newcomer"

        # 潜水者：几乎不发言
        elif message_ratio < 0.01:
            return "lurker"

        # 普通成员
        else:
            return "regular"

    def _calculate_influence_score(
        self,
        user_id: str,
        message_count: int,
        interaction_matrix: Dict[str, Dict[str, int]],
    ) -> float:
        """
        计算用户影响力分数

        考虑因素：
        1. 发言数
        2. 被回复/提及次数
        3. 互动的广度

        Returns:
            影响力分数 0.0-100.0
        """
        # 被其他人互动的次数
        mentioned_by_count = 0
        for uid, targets in interaction_matrix.items():
            if uid != user_id:
                mentioned_by_count += targets.get(user_id, 0)

        # 自己互动的用户数（广度）
        interaction_breadth = len(interaction_matrix.get(user_id, {}))

        # 综合评分
        score = (
            message_count * 0.4 +  # 发言数权重
            mentioned_by_count * 0.5 +  # 被互动权重
            interaction_breadth * 0.1  # 互动广度权重
        )

        return min(100.0, score)

    def _detect_cliques(
        self,
        interaction_matrix: Dict[str, Dict[str, int]],
        min_clique_size: int = 3,
        min_interaction: int = 3,
    ) -> List[Set[str]]:
        """
        检测小团体（互相频繁互动的用户组）

        简化版算法：寻找互相有较多互动的用户集合

        Args:
            interaction_matrix: 互动矩阵
            min_clique_size: 最小团体规模
            min_interaction: 最小互动次数

        Returns:
            小团体列表
        """
        # 构建强连接用户对
        strong_pairs = set()
        for user_id, targets in interaction_matrix.items():
            for target_id, count in targets.items():
                # 双向互动且次数足够
                reverse_count = interaction_matrix.get(target_id, {}).get(user_id, 0)
                if count >= min_interaction and reverse_count >= min_interaction:
                    pair = tuple(sorted([user_id, target_id]))
                    strong_pairs.add(pair)

        # 寻找连通的用户组
        cliques = []
        used_users = set()

        for user1, user2 in strong_pairs:
            if user1 in used_users or user2 in used_users:
                continue

            # 尝试扩展这个团体
            clique = {user1, user2}

            for user_id in interaction_matrix.keys():
                if user_id in clique:
                    continue

                # 检查这个用户是否与团体中所有人都有强互动
                connected_to_all = all(
                    interaction_matrix.get(user_id, {}).get(member, 0) >= min_interaction
                    for member in clique
                )

                if connected_to_all:
                    clique.add(user_id)

            if len(clique) >= min_clique_size:
                cliques.append(clique)
                used_users.update(clique)

        return cliques

    def _calculate_strong_relationships(
        self,
        interaction_matrix: Dict[str, Dict[str, int]],
        top_n: int = 10,
    ) -> List[Tuple[str, str, float]]:
        """
        计算强关系（互动最频繁的用户对）

        Returns:
            [(user1, user2, strength)]
        """
        relationships = []

        for user_id, targets in interaction_matrix.items():
            for target_id, count in targets.items():
                # 计算双向互动强度
                reverse_count = interaction_matrix.get(target_id, {}).get(user_id, 0)
                strength = (count + reverse_count) / 2.0

                # 避免重复（只添加一次user1-user2对）
                pair = tuple(sorted([user_id, target_id]))
                relationships.append((pair[0], pair[1], strength))

        # 去重并排序
        unique_relationships = {}
        for u1, u2, strength in relationships:
            key = (u1, u2)
            if key not in unique_relationships or unique_relationships[key] < strength:
                unique_relationships[key] = strength

        sorted_relationships = sorted(
            [(u1, u2, s) for (u1, u2), s in unique_relationships.items()],
            key=lambda x: x[2],
            reverse=True,
        )

        return sorted_relationships[:top_n]

    def get_social_network_status(self, chat_id: str, chat_name: str = "") -> SocialNetworkStatus:
        """
        获取社交网络状态

        Args:
            chat_id: 聊天ID
            chat_name: 聊天名称

        Returns:
            SocialNetworkStatus对象
        """
        # 构建互动矩阵
        interaction_matrix = self._build_interaction_matrix(chat_id)

        # 获取用户活跃度
        activity = self.user_activity.get(chat_id, {})

        total_users = len(activity)
        active_users = len([u for u, count in activity.items() if count > 0])
        total_messages = sum(activity.values())

        if total_users == 0:
            return SocialNetworkStatus(
                chat_id=chat_id,
                chat_name=chat_name,
                timestamp=time.time(),
            )

        # 分类用户角色
        user_roles = {}
        interaction_counts = {}

        for user_id in activity.keys():
            interaction_count = sum(interaction_matrix.get(user_id, {}).values())
            interaction_counts[user_id] = interaction_count

        avg_interaction = sum(interaction_counts.values()) / len(interaction_counts) if interaction_counts else 0

        for user_id, message_count in activity.items():
            role = self._classify_user_role(
                user_id,
                message_count,
                total_messages,
                interaction_counts.get(user_id, 0),
                avg_interaction,
            )
            user_roles[user_id] = role

        # 计算影响力
        influence_scores = {}
        for user_id, message_count in activity.items():
            score = self._calculate_influence_score(user_id, message_count, interaction_matrix)
            influence_scores[user_id] = score

        top_influencers = sorted(influence_scores, key=influence_scores.get, reverse=True)[:5]

        # 检测小团体
        cliques = self._detect_cliques(interaction_matrix)

        # 计算强关系
        strong_relationships = self._calculate_strong_relationships(interaction_matrix)

        # 统计潜水者比例
        lurker_count = len([r for r in user_roles.values() if r == "lurker"])
        lurker_ratio = lurker_count / total_users if total_users > 0 else 0

        # 互动多样性（使用基尼系数的简化版）
        if interaction_counts:
            sorted_counts = sorted(interaction_counts.values())
            n = len(sorted_counts)
            index_sum = sum((i + 1) * count for i, count in enumerate(sorted_counts))
            total_sum = sum(sorted_counts)
            interaction_diversity = 1.0 - (2 * index_sum) / (n * total_sum) if total_sum > 0 else 0.0
        else:
            interaction_diversity = 0.0

        return SocialNetworkStatus(
            chat_id=chat_id,
            chat_name=chat_name,
            user_roles=user_roles,
            interaction_matrix=interaction_matrix,
            strong_relationships=strong_relationships,
            influence_scores=influence_scores,
            top_influencers=top_influencers,
            cliques=cliques,
            has_cliques=len(cliques) > 0,
            total_users=total_users,
            active_users=active_users,
            lurker_ratio=lurker_ratio,
            avg_interactions_per_user=sum(interaction_counts.values()) / len(interaction_counts) if interaction_counts else 0,
            interaction_diversity=interaction_diversity,
            timestamp=time.time(),
        )
