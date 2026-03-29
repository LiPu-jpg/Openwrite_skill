import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.radar import RadarAgent, TextRadarSource


def test_radar_agent_accepts_sync_llm_client_chat():
    class FakeClient:
        def chat(self, messages, temperature=0.6, max_tokens=4096):
            return SimpleNamespace(
                content=(
                    '[{"platform":"番茄小说","genre":"都市异能","confidence":0.87,'
                    '"concept":"程序员卷入异常系统","reasoning":"榜单中都市题材占优",'
                    '"benchmarks":["A书","B书"]}]'
                )
            )

    ctx = SimpleNamespace(client=FakeClient())
    agent = RadarAgent(ctx, sources=[TextRadarSource("都市异能榜单样本")])

    result = asyncio.run(agent.scan_market(platforms=["external"], top_n=1))

    assert len(result.platform_recommendations) == 1
    assert result.platform_recommendations[0].genre == "都市异能"
    assert result.platform_recommendations[0].platform == "番茄小说"
