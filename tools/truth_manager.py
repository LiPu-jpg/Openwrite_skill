"""真相文件管理器 - 从 InkOS 融合

管理 7 个真相文件：
1. current_state.md - 世界当前状态
2. particle_ledger.md - 资源账本
3. pending_hooks.md - 伏笔列表
4. chapter_summaries.md - 章节摘要
5. subplot_board.md - 支线进度
6. emotional_arcs.md - 情感弧线
7. character_matrix.md - 角色关系矩阵

支持状态快照和回滚。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TruthFiles:
    """真相文件集合"""

    current_state: str = ""
    particle_ledger: str = ""
    pending_hooks: str = ""
    chapter_summaries: str = ""
    subplot_board: str = ""
    emotional_arcs: str = ""
    character_matrix: str = ""


@dataclass
class StateSnapshot:
    """状态快照"""

    id: str
    chapter_number: int
    created_at: str
    files: TruthFiles


class TruthFilesManager:
    """真相文件管理器

    用法:
        manager = TruthFilesManager(project_root, novel_id)

        # 加载当前真相文件
        truth = manager.load_truth_files()

        # 更新真相文件
        manager.update_truth_files(truth, {
            "current_state": "新状态...",
            "chapter_summary": "第5章：..."
        })

        # 创建快照
        manager.create_snapshot(chapter_number=5)

        # 回滚到快照
        manager.restore_snapshot("snapshot_5")
    """

    TRUTH_FILES = [
        "current_state.md",
        "particle_ledger.md",
        "pending_hooks.md",
        "chapter_summaries.md",
        "subplot_board.md",
        "emotional_arcs.md",
        "character_matrix.md",
    ]

    def __init__(self, project_root: Path, novel_id: str):
        self.project_root = project_root.resolve()
        self.novel_id = novel_id
        self.story_dir = project_root / "data" / "novels" / novel_id / "story"
        self.snapshots_dir = project_root / "data" / "novels" / novel_id / "snapshots"

    @property
    def truth_dir(self) -> Path:
        """真相文件目录"""
        return self.story_dir

    def ensure_dirs(self):
        """确保目录存在"""
        self.truth_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def load_truth_files(self) -> TruthFiles:
        """加载所有真相文件"""
        truth = TruthFiles()

        for attr_name, filename in zip(
            [
                "current_state",
                "particle_ledger",
                "pending_hooks",
                "chapter_summaries",
                "subplot_board",
                "emotional_arcs",
                "character_matrix",
            ],
            self.TRUTH_FILES,
        ):
            file_path = self.truth_dir / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    setattr(truth, attr_name, content)
                except Exception as e:
                    logger.warning(f"Failed to load {filename}: {e}")

        return truth

    def save_truth_files(self, truth: TruthFiles):
        """保存所有真相文件"""
        self.ensure_dirs()

        for attr_name, filename in zip(
            [
                "current_state",
                "particle_ledger",
                "pending_hooks",
                "chapter_summaries",
                "subplot_board",
                "emotional_arcs",
                "character_matrix",
            ],
            self.TRUTH_FILES,
        ):
            content = getattr(truth, attr_name, "")
            file_path = self.truth_dir / filename
            try:
                file_path.write_text(content, encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to save {filename}: {e}")

    def update_truth_files(self, truth: TruthFiles, updates: Dict[str, str]):
        """更新指定的真相文件"""
        for key, value in updates.items():
            if hasattr(truth, key):
                setattr(truth, key, value)
            elif key == "chapter_summary":
                # 追加到 chapter_summaries
                truth.chapter_summaries += f"\n\n{value}"

        self.save_truth_files(truth)

    def create_snapshot(self, chapter_number: int) -> str:
        """创建状态快照

        Returns:
            快照 ID
        """
        import json

        self.ensure_dirs()

        truth = self.load_truth_files()
        snapshot_id = f"snapshot_{chapter_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        snapshot: Dict[str, Any] = {
            "id": snapshot_id,
            "chapter_number": chapter_number,
            "created_at": datetime.now().isoformat(),
            "files": {
                "current_state": truth.current_state,
                "particle_ledger": truth.particle_ledger,
                "pending_hooks": truth.pending_hooks,
                "chapter_summaries": truth.chapter_summaries,
                "subplot_board": truth.subplot_board,
                "emotional_arcs": truth.emotional_arcs,
                "character_matrix": truth.character_matrix,
            },
        }

        snapshot_path = self.snapshots_dir / f"{snapshot_id}.json"
        snapshot_path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        logger.info(f"Created snapshot: {snapshot_id}")
        return snapshot_id

    def restore_snapshot(self, snapshot_id: str) -> bool:
        """恢复到指定快照"""
        import json

        snapshot_path = self.snapshots_dir / f"{snapshot_id}.json"
        if not snapshot_path.exists():
            logger.error(f"Snapshot not found: {snapshot_id}")
            return False

        try:
            with snapshot_path.open("r", encoding="utf-8") as f:
                snapshot = json.load(f)

            truth = TruthFiles(
                current_state=snapshot["files"].get("current_state", ""),
                particle_ledger=snapshot["files"].get("particle_ledger", ""),
                pending_hooks=snapshot["files"].get("pending_hooks", ""),
                chapter_summaries=snapshot["files"].get("chapter_summaries", ""),
                subplot_board=snapshot["files"].get("subplot_board", ""),
                emotional_arcs=snapshot["files"].get("emotional_arcs", ""),
                character_matrix=snapshot["files"].get("character_matrix", ""),
            )

            self.save_truth_files(truth)
            logger.info(f"Restored snapshot: {snapshot_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore snapshot: {e}")
            return False

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """列出所有快照"""
        import json

        snapshots = []
        if not self.snapshots_dir.exists():
            return snapshots

        for path in sorted(self.snapshots_dir.glob("snapshot_*.json")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    snapshots.append(
                        {
                            "id": data.get("id", ""),
                            "chapter_number": data.get("chapter_number", 0),
                            "created_at": data.get("created_at", ""),
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to load snapshot {path}: {e}")

        return snapshots

    def filter_hooks_by_pov(
        self,
        hooks: str,
        pov_character: str,
        chapter_summaries: str,
    ) -> str:
        """POV 感知过滤伏笔（融合 InkOS pov-filter.ts）

        只返回 POV 角色应该知道的伏笔。
        """
        if not hooks or not pov_character:
            return hooks

        lines = hooks.strip().split("\n")
        filtered = []

        for line in lines:
            # 简单启发式：如果伏笔描述中提到 POV 角色或角色已知事件，则保留
            # 实际应用中应该用 LLM 分析
            if pov_character in line:
                filtered.append(line)
                continue

            # 检查章节摘要中 POV 角色是否在场
            if self._character_mentioned_in_summaries(pov_character, chapter_summaries):
                filtered.append(line)

        return "\n".join(filtered) if filtered else hooks

    def _character_mentioned_in_summaries(self, character: str, summaries: str) -> bool:
        """检查角色是否在章节摘要中提及"""
        if not summaries:
            return False

        # 简单匹配
        pattern = rf"{re.escape(character)}"
        return bool(re.search(pattern, summaries))

    def extract_facts_from_chapter(
        self,
        content: str,
        chapter_number: int,
        pov_character: Optional[str] = None,
    ) -> Dict[str, str]:
        """从章节内容中提取事实（用于更新真相文件）"""
        facts: Dict[str, str] = {}

        # 这里应该调用 LLM 来提取
        # 简化版本使用正则提取

        # 提取物品获得/失去
        items_gained = re.findall(r"获得了?(.+?)[。，！]", content)
        items_lost = re.findall(r"失去了?(.+?)[。，！]", content)

        if items_gained:
            facts["items_gained"] = items_gained
        if items_lost:
            facts["items_lost"] = items_lost

        # 提取数值变化
        money_changes = re.findall(r"(\d+)\s*(?:金币|元|银两|晶石)", content)
        if money_changes:
            facts["money_changes"] = [int(m) for m in money_changes]

        # 提取新角色
        new_characters = re.findall(r"(?:新角色|登场)：(.+?)[。，]", content)
        if new_characters:
            facts["new_characters"] = new_characters

        # 提取关系变化
        relationship_changes = re.findall(
            r"(?:关系|情感|感觉).*?(?:对|给|与).*?[是变成成为了](.+?)[。，]", content
        )
        if relationship_changes:
            facts["relationship_changes"] = relationship_changes

        return facts
