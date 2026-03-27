"""伏笔系统数据模型"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ForeshadowingNode(BaseModel):
    """伏笔节点

    回收目标说明:
    - target_arc: 目标篇章（如 arc_001），最宽松
    - target_section: 目标节（如 sec_003），中等
    - target_chapter: 目标章节（如 ch_010），最精确
    三者可以组合使用，表示"大概在第X篇第Y节的第Z章左右回收"
    """

    id: str = Field(..., description="伏笔 ID")
    content: str = Field(..., description="伏笔内容描述")
    weight: int = Field(..., ge=1, le=10, description="权重 1-10")
    layer: str = Field(..., description="主线/支线/彩蛋")
    status: str = Field(..., description="埋伏/待收/已收/废弃")
    created_at: str = Field(..., description="创建位置（章节/节/篇均可）")
    target_arc: Optional[str] = Field(None, description="预期回收篇章（如 arc_002）")
    target_section: Optional[str] = Field(None, description="预期回收节（如 sec_003）")
    target_chapter: Optional[str] = Field(None, description="预期回收章节（如 ch_010）")
    tags: List[str] = Field(default_factory=list, description="标签")


class ForeshadowingEdge(BaseModel):
    """伏笔 DAG 边"""

    model_config = {"populate_by_name": True}

    from_: str = Field(..., alias="from", description="来源伏笔 ID")
    to: str = Field(..., description="目标伏笔 ID 或回收点")
    type: str = Field(..., description="依赖/强化/反转")


class ForeshadowingGraph(BaseModel):
    """伏笔 DAG 图"""

    nodes: Dict[str, ForeshadowingNode] = Field(default_factory=dict, description="所有伏笔节点")
    edges: List[ForeshadowingEdge] = Field(default_factory=list, description="伏笔关系边")
    status: Dict[str, str] = Field(default_factory=dict, description="节点状态映射")
