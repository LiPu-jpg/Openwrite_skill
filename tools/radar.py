"""雷达市场分析 - 从 InkOS radar.ts 融合

扫描市场趋势，分析热门题材，为创作决策提供参考。

支持：
1. 真实数据抓取（番茄API、起点爬取）
2. LLM 分析趋势
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class RankingEntry:
    """排行榜条目"""

    title: str
    author: str
    category: str
    extra: str


@dataclass
class PlatformRankings:
    """平台排行榜数据"""

    platform: str
    entries: list[RankingEntry]


@dataclass
class PlatformRecommendation:
    """平台推荐"""

    platform: str
    genre: str
    confidence: float
    concept: str
    reasoning: str
    benchmarks: list[str]


@dataclass
class MarketAnalysisResult:
    """市场分析结果"""

    timestamp: str
    platform_recommendations: list[PlatformRecommendation]
    trends: list[str]
    raw_data: dict


class RadarSource:
    """雷达数据源基类"""

    name: str = ""

    async def fetch(self) -> PlatformRankings:
        raise NotImplementedError


class FanqieRadarSource(RadarSource):
    """番茄小说 API 数据源

    调用番茄内部 API 获取排行榜数据。
    """

    name = "番茄小说"

    async def fetch(self) -> PlatformRankings:
        """获取番茄小说排行榜"""
        import urllib.request

        entries = []
        fanqie_api_urls = [
            (
                "https://api-lf.fanqiesdk.com/api/novel/channel/homepage/rank/rank_list/v2/?aid=13&limit=20&offset=0&side_type=10",
                "热门榜",
            ),
            (
                "https://api-lf.fanqiesdk.com/api/novel/channel/homepage/rank/rank_list/v2/?aid=13&limit=20&offset=0&side_type=13",
                "黑马榜",
            ),
        ]

        for url, label in fanqie_api_urls:
            try:
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; OpenWrite/1.0)",
                        "Accept": "application/json",
                    },
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))

                items = data.get("data", {}).get("result", []) if isinstance(data, dict) else []
                for item in items[:15]:
                    if isinstance(item, dict):
                        entries.append(
                            RankingEntry(
                                title=str(item.get("book_name", "")),
                                author=str(item.get("author", "")),
                                category=str(item.get("category", "")),
                                extra=f"[{label}]",
                            )
                        )
            except Exception as e:
                logger.warning(f"番茄 API 请求失败: {e}")

        return PlatformRankings(platform=self.name, entries=entries)


class QidianRadarSource(RadarSource):
    """起点中文网页面爬取

    爬取起点排行榜页面提取书名。
    """

    name = "起点中文网"

    async def fetch(self) -> PlatformRankings:
        """获取起点排行榜"""
        import urllib.request

        entries = []
        qidian_url = "https://www.qidian.com/rank/"

        try:
            req = urllib.request.Request(
                qidian_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")

            seen = set()
            book_pattern = re.compile(
                r'<a[^>]*href="//book\.qidian\.com/info/\d+"[^>]*>([^<]+)</a>'
            )
            for match in book_pattern.finditer(html):
                title = match.group(1).strip()
                if title and title not in seen and 1 < len(title) < 30:
                    seen.add(title)
                    entries.append(
                        RankingEntry(
                            title=title,
                            author="",
                            category="",
                            extra="[起点推荐榜]",
                        )
                    )
                    if len(entries) >= 20:
                        break
        except Exception as e:
            logger.warning(f"起点爬取失败: {e}")

        return PlatformRankings(platform=self.name, entries=entries)


class TextRadarSource(RadarSource):
    """文本数据源（用于注入外部分析）"""

    name = "external"

    def __init__(self, text: str):
        self.text = text

    async def fetch(self) -> PlatformRankings:
        return PlatformRankings(
            platform=self.name,
            entries=[
                RankingEntry(
                    title=self.text,
                    author="",
                    category="",
                    extra="[外部分析]",
                )
            ],
        )


class RadarAgent:
    """雷达市场分析 Agent

    支持真实数据抓取 + LLM 分析：

    用法:
        radar = RadarAgent(ctx)
        result = await radar.scan_market()

        for rec in result.platform_recommendations:
            print(f"[{rec.confidence:.0%}] {rec.platform}/{rec.genre}: {rec.concept}")
    """

    def __init__(self, agent_ctx: Any, sources: Optional[list[RadarSource]] = None):
        """初始化雷达

        Args:
            agent_ctx: Agent 上下文（需要 client, model）
            sources: 数据源列表（默认使用番茄和起点）
        """
        self.ctx = agent_ctx
        self.log = logger.getChild("radar")
        self.sources = sources or [FanqieRadarSource(), QidianRadarSource()]

    async def scan_market(
        self,
        platforms: Optional[list[str]] = None,
        top_n: int = 5,
    ) -> MarketAnalysisResult:
        """扫描市场

        Args:
            platforms: 要扫描的平台列表（默认全部）
            top_n: 每个平台返回的推荐数量

        Returns:
            MarketAnalysisResult
        """
        platforms = platforms or [s.name for s in self.sources]

        rankings: list[PlatformRankings] = []
        for source in self.sources:
            if source.name in platforms or not platforms:
                try:
                    data = await source.fetch()
                    rankings.append(data)
                    self.log.info(f"抓取 {source.name}: {len(data.entries)} 条")
                except Exception as e:
                    self.log.warning(f"抓取 {source.name} 失败: {e}")

        rankings_text = self._format_rankings(rankings)
        recommendations = await self._analyze_with_llm(rankings_text, top_n)
        trends = self._extract_trends(recommendations)

        return MarketAnalysisResult(
            timestamp=datetime.now().isoformat(),
            platform_recommendations=recommendations,
            trends=trends,
            raw_data={
                "rankings": [{"platform": r.platform, "entries": len(r.entries)} for r in rankings]
            },
        )

    def _format_rankings(self, rankings: list[PlatformRankings]) -> str:
        """格式化排行榜数据给 LLM"""
        sections = []
        for r in rankings:
            if r.entries:
                lines = []
                for e in r.entries[:15]:
                    author_part = f" ({e.author})" if e.author else ""
                    category_part = f" [{e.category}]" if e.category else ""
                    lines.append(f"- {e.title}{author_part}{category_part} {e.extra}")
                sections.append(f"### {r.platform}\n" + "\n".join(lines))
        return "\n\n".join(sections) if sections else "（未能获取到实时排行数据）"

    async def _analyze_with_llm(
        self, rankings_text: str, top_n: int
    ) -> list[PlatformRecommendation]:
        """用 LLM 分析排行榜数据"""
        from .llm import Message

        system_prompt = f"""你是一个专业的网络小说市场分析师。下面是从各平台实时抓取的排行榜数据，请基于这些真实数据分析市场趋势。

## 实时排行榜数据

{rankings_text}

分析维度：
1. 从排行榜数据中识别当前热门题材和标签
2. 分析哪些类型的作品占据榜单高位
3. 发现市场空白和机会点
4. 风险提示（榜单上过度扎堆的题材）

输出格式必须为 JSON：
```json
[
  {{
    "platform": "平台名",
    "genre": "题材类型",
    "confidence": 0.0-1.0,
    "concept": "一句话概念描述",
    "reasoning": "推荐理由（引用具体榜单数据）",
    "benchmarks": ["对标书1", "对标书2"]
  }}
]
```

推荐 3-5 个，按 confidence 降序排列。只返回 JSON。"""

        user_prompt = "请基于上面的实时排行榜数据，分析当前网文市场热度，给出开书建议。"

        try:
            response = await self.ctx.client.chat(
                messages=[
                    Message("system", system_prompt),
                    Message("user", user_prompt),
                ],
                temperature=0.6,
                max_tokens=4096,
            )

            return self._parse_recommendations(response.content)
        except Exception as e:
            self.log.error(f"LLM analysis failed: {e}")
            return []

    def _parse_recommendations(self, content: str) -> list[PlatformRecommendation]:
        """解析 LLM 输出"""
        recommendations = []

        try:
            json_match = re.search(r"\[.*\]", content, re.DOTALL)
            if json_match:
                items = json.loads(json_match.group(0))
                for item in items:
                    recommendations.append(
                        PlatformRecommendation(
                            platform=item.get("platform", ""),
                            genre=item.get("genre", "unknown"),
                            confidence=item.get("confidence", 0.5),
                            concept=item.get("concept", ""),
                            reasoning=item.get("reasoning", ""),
                            benchmarks=item.get("benchmarks", []),
                        )
                    )
        except json.JSONDecodeError as e:
            self.log.warning(f"Failed to parse JSON: {e}")

        return recommendations

    def _extract_trends(self, recommendations: list[PlatformRecommendation]) -> list[str]:
        """提取趋势"""
        trends = []

        genre_count: dict[str, int] = {}
        for rec in recommendations:
            genre_count[rec.genre] = genre_count.get(rec.genre, 0) + 1

        if genre_count:
            top_genre = max(genre_count, key=genre_count.get)
            trends.append(f"最热题材：{top_genre}（出现在{genre_count[top_genre]}个推荐中）")

        concepts = " ".join(r.concept for r in recommendations)
        keywords = self._extract_keywords(concepts)
        if keywords:
            trends.append(f"热门关键词：{', '.join(keywords)}")

        return trends

    def _extract_keywords(self, text: str) -> list[str]:
        """提取关键词"""
        keyword_patterns = [
            "穿越",
            "系统",
            "重生",
            "退婚",
            "升级",
            "修炼",
            "都市",
            "异界",
            "末世",
            "星际",
            "直播",
            "游戏",
            "洪荒",
            "御兽",
            "无敌",
            "甜宠",
            "虐文",
            "乡村",
            "异能",
        ]
        found = [kw for kw in keyword_patterns if kw in text]
        return found[:5]

    def save_result(self, result: MarketAnalysisResult, output_path: str):
        """保存分析结果"""
        import os

        dir_path = os.path.dirname(output_path) or "."
        os.makedirs(dir_path, exist_ok=True)

        data = {
            "timestamp": result.timestamp,
            "recommendations": [
                {
                    "platform": r.platform,
                    "genre": r.genre,
                    "confidence": r.confidence,
                    "concept": r.concept,
                    "reasoning": r.reasoning,
                    "benchmarks": r.benchmarks,
                }
                for r in result.platform_recommendations
            ],
            "trends": result.trends,
            "raw_data": result.raw_data,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.log.info(f"Saved to {output_path}")
