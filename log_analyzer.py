#!/usr/bin/env python3
"""
Log Analysis Utility for Rubix Token Sync System

Provides comprehensive log analysis, error pattern detection, and performance monitoring
for the distributed token sync operations.
"""

import os
import re
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter
import argparse
import pandas as pd

class LogAnalyzer:
    """Comprehensive log analyzer for sync operations"""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = Path(logs_dir)
        self.log_patterns = {
            'timestamp': r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            'level': r'- (DEBUG|INFO|WARNING|ERROR|CRITICAL) -',
            'component': r'- ([A-Z]+):([A-Z_]+) \[([^\]]+)\]',
            'correlation_id': r'\[([a-f0-9]{8})\]',
            'ipfs_operation': r'IPFS (FETCH) for token ([^:]+): (SUCCESS|FAILED)',
            'sql_operation': r'Database ([^:]+): (SUCCESS|FAILED)',
            'validation': r'Validation ([^:]+) for token ([^:]+): (PASSED|FAILED)',
            'progress': r'Progress: ([\d.]+)% \| Records: ([\d,]+) \| Rate: ([\d.]+)/sec',
            'bulk_insert': r'Bulk insert completed successfully: (\d+) records',
            'error_stack': r'Stack Trace: (.+?)(?=\n\d{4}-\d{2}-\d{2}|\Z)',
        }

    def get_log_files(self, pattern: str = "*.log") -> List[Path]:
        """Get all log files matching the pattern"""
        if not self.logs_dir.exists():
            return []
        return list(self.logs_dir.glob(pattern))

    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """Parse a single log line and extract structured data"""
        parsed = {
            'raw_line': line.strip(),
            'timestamp': None,
            'level': None,
            'component': None,
            'operation': None,
            'correlation_id': None,
            'message': None
        }

        # Extract timestamp
        timestamp_match = re.search(self.log_patterns['timestamp'], line)
        if timestamp_match:
            try:
                parsed['timestamp'] = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass

        # Extract log level
        level_match = re.search(self.log_patterns['level'], line)
        if level_match:
            parsed['level'] = level_match.group(1)

        # Extract component and operation
        component_match = re.search(self.log_patterns['component'], line)
        if component_match:
            parsed['component'] = component_match.group(1)
            parsed['operation'] = component_match.group(2)
            parsed['correlation_id'] = component_match.group(3)

        # Extract message (everything after the structured part)
        message_start = line.find('] - ')
        if message_start != -1:
            parsed['message'] = line[message_start + 4:].strip()

        return parsed

    def analyze_performance_metrics(self, log_files: List[Path] = None) -> Dict[str, Any]:
        """Analyze performance metrics from log files"""
        if log_files is None:
            log_files = self.get_log_files("sync_main_*.log")

        metrics = {
            'total_records_processed': 0,
            'avg_processing_rate': 0,
            'ipfs_operations': {'success': 0, 'failed': 0},
            'sql_operations': {'success': 0, 'failed': 0},
            'validation_results': {'passed': 0, 'failed': 0},
            'bulk_inserts': [],
            'error_patterns': Counter(),
            'hourly_performance': defaultdict(list),
            'component_performance': defaultdict(list)
        }

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        self._process_performance_line(line, metrics)
            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        # Calculate averages
        if metrics['ipfs_operations']['success'] + metrics['ipfs_operations']['failed'] > 0:
            metrics['ipfs_success_rate'] = (
                metrics['ipfs_operations']['success'] /
                (metrics['ipfs_operations']['success'] + metrics['ipfs_operations']['failed']) * 100
            )
        else:
            metrics['ipfs_success_rate'] = 0

        if metrics['sql_operations']['success'] + metrics['sql_operations']['failed'] > 0:
            metrics['sql_success_rate'] = (
                metrics['sql_operations']['success'] /
                (metrics['sql_operations']['success'] + metrics['sql_operations']['failed']) * 100
            )
        else:
            metrics['sql_success_rate'] = 0

        return metrics

    def _process_performance_line(self, line: str, metrics: Dict[str, Any]):
        """Process a single line for performance metrics"""
        # Progress tracking
        progress_match = re.search(self.log_patterns['progress'], line)
        if progress_match:
            progress_pct = float(progress_match.group(1))
            records_str = progress_match.group(2).replace(',', '')
            rate = float(progress_match.group(3))

            metrics['total_records_processed'] = max(metrics['total_records_processed'], int(records_str))
            metrics['avg_processing_rate'] = rate

            # Track hourly performance
            parsed = self.parse_log_line(line)
            if parsed['timestamp']:
                hour_key = parsed['timestamp'].strftime('%Y-%m-%d %H:00')
                metrics['hourly_performance'][hour_key].append(rate)

        # IPFS operations
        ipfs_match = re.search(self.log_patterns['ipfs_operation'], line)
        if ipfs_match:
            if ipfs_match.group(3) == 'SUCCESS':
                metrics['ipfs_operations']['success'] += 1
            else:
                metrics['ipfs_operations']['failed'] += 1

        # SQL operations
        sql_match = re.search(self.log_patterns['sql_operation'], line)
        if sql_match:
            if sql_match.group(2) == 'SUCCESS':
                metrics['sql_operations']['success'] += 1
            else:
                metrics['sql_operations']['failed'] += 1

        # Validation results
        validation_match = re.search(self.log_patterns['validation'], line)
        if validation_match:
            if validation_match.group(3) == 'PASSED':
                metrics['validation_results']['passed'] += 1
            else:
                metrics['validation_results']['failed'] += 1

        # Bulk inserts
        bulk_match = re.search(self.log_patterns['bulk_insert'], line)
        if bulk_match:
            record_count = int(bulk_match.group(1))
            parsed = self.parse_log_line(line)
            metrics['bulk_inserts'].append({
                'timestamp': parsed['timestamp'],
                'record_count': record_count
            })

        # Error patterns
        if ' ERROR ' in line or ' CRITICAL ' in line:
            # Extract error type from message
            if 'timeout' in line.lower():
                metrics['error_patterns']['timeout'] += 1
            elif 'connection' in line.lower():
                metrics['error_patterns']['connection'] += 1
            elif 'validation' in line.lower():
                metrics['error_patterns']['validation'] += 1
            elif 'ipfs' in line.lower():
                metrics['error_patterns']['ipfs'] += 1
            elif 'database' in line.lower() or 'sql' in line.lower():
                metrics['error_patterns']['database'] += 1
            else:
                metrics['error_patterns']['other'] += 1

    def analyze_error_patterns(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze error patterns from the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        error_files = self.get_log_files("sync_errors_*.log")

        error_analysis = {
            'total_errors': 0,
            'error_by_component': Counter(),
            'error_by_type': Counter(),
            'error_timeline': [],
            'top_error_messages': Counter(),
            'correlation_chains': defaultdict(list)
        }

        for error_file in error_files:
            try:
                with open(error_file, 'r', encoding='utf-8') as f:
                    current_error = None
                    stack_trace = []

                    for line in f:
                        parsed = self.parse_log_line(line)

                        if parsed['timestamp'] and parsed['timestamp'] < cutoff_time:
                            continue

                        if parsed['level'] in ['ERROR', 'CRITICAL']:
                            if current_error:
                                # Save previous error
                                current_error['stack_trace'] = '\n'.join(stack_trace)
                                error_analysis['error_timeline'].append(current_error)

                            # Start new error
                            current_error = {
                                'timestamp': parsed['timestamp'],
                                'component': parsed['component'],
                                'operation': parsed['operation'],
                                'correlation_id': parsed['correlation_id'],
                                'message': parsed['message'],
                                'level': parsed['level']
                            }
                            stack_trace = []

                            error_analysis['total_errors'] += 1
                            error_analysis['error_by_component'][parsed['component']] += 1

                            # Categorize error type
                            message_lower = parsed['message'].lower() if parsed['message'] else ''
                            if 'timeout' in message_lower:
                                error_analysis['error_by_type']['timeout'] += 1
                            elif 'connection' in message_lower:
                                error_analysis['error_by_type']['connection'] += 1
                            elif 'permission' in message_lower or 'access' in message_lower:
                                error_analysis['error_by_type']['permission'] += 1
                            elif 'validation' in message_lower:
                                error_analysis['error_by_type']['validation'] += 1
                            else:
                                error_analysis['error_by_type']['other'] += 1

                            error_analysis['top_error_messages'][parsed['message'][:100]] += 1

                            # Track correlation chains
                            if parsed['correlation_id']:
                                error_analysis['correlation_chains'][parsed['correlation_id']].append(current_error)

                        elif current_error and 'Stack Trace:' in line:
                            stack_trace.append(line.strip())

                    # Don't forget the last error
                    if current_error:
                        current_error['stack_trace'] = '\n'.join(stack_trace)
                        error_analysis['error_timeline'].append(current_error)

            except Exception as e:
                print(f"Error analyzing {error_file}: {e}")

        return error_analysis

    def generate_summary_report(self, hours: int = 24) -> str:
        """Generate a comprehensive summary report"""
        performance = self.analyze_performance_metrics()
        errors = self.analyze_error_patterns(hours)

        report = [
            "=" * 80,
            f"RUBIX TOKEN SYNC - LOG ANALYSIS REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Analysis Period: Last {hours} hours",
            "=" * 80,
            "",
            "📊 PERFORMANCE SUMMARY",
            "-" * 40,
            f"Total Records Processed: {performance['total_records_processed']:,}",
            f"Average Processing Rate: {performance['avg_processing_rate']:.1f} records/sec",
            f"IPFS Success Rate: {performance['ipfs_success_rate']:.1f}%",
            f"SQL Success Rate: {performance['sql_success_rate']:.1f}%",
            f"Validation Pass Rate: {(performance['validation_results']['passed'] / max(performance['validation_results']['passed'] + performance['validation_results']['failed'], 1)) * 100:.1f}%",
            "",
            "🔍 OPERATION BREAKDOWN",
            "-" * 40,
            f"IPFS Operations: {performance['ipfs_operations']['success']:,} success, {performance['ipfs_operations']['failed']:,} failed",
            f"SQL Operations: {performance['sql_operations']['success']:,} success, {performance['sql_operations']['failed']:,} failed",
            f"Bulk Inserts: {len(performance['bulk_inserts'])} operations",
            "",
            "⚠️  ERROR ANALYSIS",
            "-" * 40,
            f"Total Errors: {errors['total_errors']:,}",
            f"Error Rate: {(errors['total_errors'] / max(performance['total_records_processed'], 1)) * 100:.3f}%",
            "",
            "Top Error Types:",
        ]

        for error_type, count in errors['error_by_type'].most_common(5):
            report.append(f"  {error_type}: {count:,}")

        report.extend([
            "",
            "Top Error Components:",
        ])

        for component, count in errors['error_by_component'].most_common(5):
            report.append(f"  {component}: {count:,}")

        if performance['hourly_performance']:
            report.extend([
                "",
                "📈 HOURLY PERFORMANCE TRENDS",
                "-" * 40,
            ])

            for hour, rates in sorted(performance['hourly_performance'].items())[-24:]:
                avg_rate = sum(rates) / len(rates) if rates else 0
                report.append(f"  {hour}: {avg_rate:.1f} records/sec (samples: {len(rates)})")

        report.extend([
            "",
            "🔧 RECOMMENDATIONS",
            "-" * 40,
        ])

        # Add recommendations based on analysis
        if performance['ipfs_success_rate'] < 90:
            report.append("  • IPFS success rate is low - consider increasing timeout or reducing parallelism")

        if performance['sql_success_rate'] < 95:
            report.append("  • SQL errors detected - check database connection and constraints")

        if errors['error_by_type']['timeout'] > errors['total_errors'] * 0.3:
            report.append("  • High timeout rate - consider optimizing network or increasing timeouts")

        if len(performance['bulk_inserts']) == 0 and performance['total_records_processed'] > 10000:
            report.append("  • No bulk inserts detected - verify bulk insert threshold settings")

        report.extend([
            "",
            "=" * 80,
        ])

        return '\n'.join(report)

    def export_metrics_to_csv(self, output_file: str):
        """Export performance metrics to CSV for analysis"""
        performance = self.analyze_performance_metrics()
        errors = self.analyze_error_patterns()

        # Create DataFrame with hourly metrics
        hourly_data = []
        for hour, rates in performance['hourly_performance'].items():
            if rates:
                hourly_data.append({
                    'hour': hour,
                    'avg_rate': sum(rates) / len(rates),
                    'min_rate': min(rates),
                    'max_rate': max(rates),
                    'samples': len(rates)
                })

        if hourly_data:
            df = pd.DataFrame(hourly_data)
            df.to_csv(output_file, index=False)
            print(f"Metrics exported to: {output_file}")
        else:
            print("No hourly performance data available for export")

def main():
    parser = argparse.ArgumentParser(description='Analyze Rubix Token Sync logs')
    parser.add_argument('--logs-dir', default='logs', help='Directory containing log files')
    parser.add_argument('--hours', type=int, default=24, help='Hours to analyze (default: 24)')
    parser.add_argument('--export-csv', help='Export metrics to CSV file')
    parser.add_argument('--errors-only', action='store_true', help='Show only error analysis')

    args = parser.parse_args()

    analyzer = LogAnalyzer(args.logs_dir)

    if args.errors_only:
        errors = analyzer.analyze_error_patterns(args.hours)
        print(json.dumps(errors, indent=2, default=str))
    else:
        report = analyzer.generate_summary_report(args.hours)
        print(report)

    if args.export_csv:
        analyzer.export_metrics_to_csv(args.export_csv)

if __name__ == "__main__":
    main()