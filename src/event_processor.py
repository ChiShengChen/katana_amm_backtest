"""
事件處理器：讀取和解析 JSONL 事件數據
"""
import json
from typing import Iterator, Dict, Any, Optional
from pathlib import Path


class EventProcessor:
    """處理池子事件數據"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
    
    def read_events(self) -> Iterator[Dict[str, Any]]:
        """讀取所有事件（生成器）"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        event = json.loads(line)
                        yield event
                    except json.JSONDecodeError as e:
                        print(f"Error parsing line: {e}")
                        continue
    
    def get_events_by_type(self, event_type: str) -> Iterator[Dict[str, Any]]:
        """按事件類型過濾"""
        for event in self.read_events():
            if event.get('eventType') == event_type:
                yield event
    
    def get_events_in_range(
        self,
        start_block: Optional[int] = None,
        end_block: Optional[int] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None
    ) -> Iterator[Dict[str, Any]]:
        """獲取指定範圍內的事件"""
        for event in self.read_events():
            block_num = event.get('blockNumber')
            timestamp = event.get('blockTimestamp')
            
            if start_block and block_num and block_num < start_block:
                continue
            if end_block and block_num and block_num > end_block:
                continue
            if start_timestamp and timestamp and timestamp < start_timestamp:
                continue
            if end_timestamp and timestamp and timestamp > end_timestamp:
                continue
            
            yield event
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """獲取事件統計信息"""
        stats = {
            'total': 0,
            'by_type': {},
            'block_range': {'min': None, 'max': None},
            'timestamp_range': {'min': None, 'max': None}
        }
        
        for event in self.read_events():
            stats['total'] += 1
            
            event_type = event.get('eventType', 'Unknown')
            stats['by_type'][event_type] = stats['by_type'].get(event_type, 0) + 1
            
            block_num = event.get('blockNumber')
            if block_num:
                if stats['block_range']['min'] is None or block_num < stats['block_range']['min']:
                    stats['block_range']['min'] = block_num
                if stats['block_range']['max'] is None or block_num > stats['block_range']['max']:
                    stats['block_range']['max'] = block_num
            
            timestamp = event.get('blockTimestamp')
            if timestamp:
                if stats['timestamp_range']['min'] is None or timestamp < stats['timestamp_range']['min']:
                    stats['timestamp_range']['min'] = timestamp
                if stats['timestamp_range']['max'] is None or timestamp > stats['timestamp_range']['max']:
                    stats['timestamp_range']['max'] = timestamp
        
        return stats

