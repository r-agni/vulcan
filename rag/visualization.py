"""
Chart and diagram generation for RAG chat responses
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server use

import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

# Set seaborn style
sns.set_theme(style="whitegrid")


class ChartGenerator:
    """Generate charts and diagrams from analytics data"""

    def __init__(self, figsize: Tuple[int, int] = (10, 6), dpi: int = 100):
        """
        Initialize chart generator

        Args:
            figsize: Default figure size (width, height)
            dpi: Dots per inch for output images
        """
        self.figsize = figsize
        self.dpi = dpi

    def _fig_to_base64(self, fig) -> str:
        """
        Convert matplotlib figure to base64 encoded PNG

        Args:
            fig: Matplotlib figure object

        Returns:
            Base64 encoded PNG string
        """
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

    def generate_line_chart(
        self,
        data: Dict[str, List],
        x_key: str,
        y_key: str,
        title: str = "Line Chart",
        xlabel: str = None,
        ylabel: str = None,
        multiple_lines: List[str] = None
    ) -> str:
        """
        Generate line chart

        Args:
            data: Dictionary with data lists
            x_key: Key for x-axis data
            y_key: Key for y-axis data
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            multiple_lines: List of keys for multiple line plots

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        if multiple_lines:
            for line_key in multiple_lines:
                ax.plot(data[x_key], data[line_key], marker='o', label=line_key)
            ax.legend()
        else:
            ax.plot(data[x_key], data[y_key], marker='o', linewidth=2)

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel(xlabel or x_key, fontsize=12)
        ax.set_ylabel(ylabel or y_key, fontsize=12)
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels if they're dates or long strings
        plt.xticks(rotation=45, ha='right')

        return self._fig_to_base64(fig)

    def generate_bar_chart(
        self,
        data: Dict[str, List],
        x_key: str,
        y_key: str,
        title: str = "Bar Chart",
        xlabel: str = None,
        ylabel: str = None,
        horizontal: bool = False
    ) -> str:
        """
        Generate bar chart

        Args:
            data: Dictionary with data lists
            x_key: Key for x-axis (categories)
            y_key: Key for y-axis (values)
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            horizontal: If True, create horizontal bar chart

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        x_data = data[x_key]
        y_data = data[y_key]

        if horizontal:
            ax.barh(x_data, y_data, color=sns.color_palette("husl", len(x_data)))
            ax.set_ylabel(xlabel or x_key, fontsize=12)
            ax.set_xlabel(ylabel or y_key, fontsize=12)
        else:
            ax.bar(x_data, y_data, color=sns.color_palette("husl", len(x_data)))
            ax.set_xlabel(xlabel or x_key, fontsize=12)
            ax.set_ylabel(ylabel or y_key, fontsize=12)
            plt.xticks(rotation=45, ha='right')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y' if not horizontal else 'x')

        return self._fig_to_base64(fig)

    def generate_pie_chart(
        self,
        data: Dict[str, List],
        labels_key: str,
        values_key: str,
        title: str = "Pie Chart"
    ) -> str:
        """
        Generate pie chart

        Args:
            data: Dictionary with data lists
            labels_key: Key for labels
            values_key: Key for values
            title: Chart title

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        labels = data[labels_key]
        values = data[values_key]

        colors = sns.color_palette("husl", len(labels))
        ax.pie(values, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.axis('equal')

        return self._fig_to_base64(fig)

    def generate_heatmap(
        self,
        data: Dict[str, Any],
        title: str = "Heatmap",
        cmap: str = "YlOrRd"
    ) -> str:
        """
        Generate heatmap

        Args:
            data: 2D array or DataFrame-compatible data
            title: Chart title
            cmap: Colormap name

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        # Convert to DataFrame if necessary
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = data

        sns.heatmap(df, annot=True, fmt='.1f', cmap=cmap, ax=ax, cbar_kws={'label': 'Value'})
        ax.set_title(title, fontsize=14, fontweight='bold')

        return self._fig_to_base64(fig)

    def generate_scatter_plot(
        self,
        data: Dict[str, List],
        x_key: str,
        y_key: str,
        title: str = "Scatter Plot",
        xlabel: str = None,
        ylabel: str = None,
        color_key: str = None,
        size_key: str = None
    ) -> str:
        """
        Generate scatter plot

        Args:
            data: Dictionary with data lists
            x_key: Key for x-axis data
            y_key: Key for y-axis data
            title: Chart title
            xlabel: X-axis label
            ylabel: Y-axis label
            color_key: Key for color coding points
            size_key: Key for sizing points

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        x_data = data[x_key]
        y_data = data[y_key]

        scatter_kwargs = {}
        if color_key and color_key in data:
            scatter_kwargs['c'] = data[color_key]
            scatter_kwargs['cmap'] = 'viridis'
        if size_key and size_key in data:
            scatter_kwargs['s'] = np.array(data[size_key]) * 10

        scatter = ax.scatter(x_data, y_data, alpha=0.6, **scatter_kwargs)

        if color_key and color_key in data:
            plt.colorbar(scatter, ax=ax, label=color_key)

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel(xlabel or x_key, fontsize=12)
        ax.set_ylabel(ylabel or y_key, fontsize=12)
        ax.grid(True, alpha=0.3)

        return self._fig_to_base64(fig)

    def generate_timeline(
        self,
        data: Dict[str, List],
        time_key: str,
        value_key: str,
        title: str = "Timeline",
        ylabel: str = None,
        events: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate timeline chart

        Args:
            data: Dictionary with data lists
            time_key: Key for time/date data
            value_key: Key for value data
            title: Chart title
            ylabel: Y-axis label
            events: List of events to mark on timeline [{"time": ..., "label": ...}]

        Returns:
            Base64 encoded PNG
        """
        fig, ax = plt.subplots(figsize=self.figsize)

        times = data[time_key]
        values = data[value_key]

        # Convert times to datetime if they're strings
        if times and isinstance(times[0], str):
            try:
                times = [datetime.fromisoformat(t.replace('Z', '+00:00')) for t in times]
            except:
                pass

        ax.plot(times, values, marker='o', linewidth=2, markersize=6)

        # Mark events if provided
        if events:
            for event in events:
                event_time = event.get('time')
                if isinstance(event_time, str):
                    try:
                        event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                    except:
                        continue
                ax.axvline(x=event_time, color='red', linestyle='--', alpha=0.5)
                ax.text(event_time, max(values), event.get('label', ''), rotation=90, va='top')

        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel(ylabel or value_key, fontsize=12)
        ax.grid(True, alpha=0.3)

        plt.xticks(rotation=45, ha='right')
        fig.autofmt_xdate()

        return self._fig_to_base64(fig)

    def generate_chart_from_query_results(
        self,
        query_results: List[Dict[str, Any]],
        chart_type: str,
        title: str = None,
        x_field: str = None,
        y_field: str = None
    ) -> str:
        """
        Auto-generate chart from RAG query results

        Args:
            query_results: List of result dictionaries from vector search
            chart_type: Type of chart ("line", "bar", "pie", "scatter", "timeline")
            title: Chart title
            x_field: Field to use for x-axis
            y_field: Field to use for y-axis

        Returns:
            Base64 encoded PNG
        """
        if not query_results:
            raise ValueError("No query results provided")

        # Extract data from query results
        data = {}
        for result in query_results:
            metadata = result.get('metadata', {})
            for key, value in metadata.items():
                if key not in data:
                    data[key] = []
                data[key].append(value)

        # Auto-detect fields if not provided
        if not x_field:
            x_field = 'timestamp' if 'timestamp' in data else list(data.keys())[0]
        if not y_field and len(data.keys()) > 1:
            numeric_fields = [k for k, v in data.items() if k != x_field and isinstance(v[0], (int, float))]
            y_field = numeric_fields[0] if numeric_fields else list(data.keys())[1]

        title = title or f"{y_field} over {x_field}"

        # Generate appropriate chart
        if chart_type == "line":
            return self.generate_line_chart(data, x_field, y_field, title=title)
        elif chart_type == "bar":
            return self.generate_bar_chart(data, x_field, y_field, title=title)
        elif chart_type == "pie":
            return self.generate_pie_chart(data, x_field, y_field, title=title)
        elif chart_type == "scatter":
            return self.generate_scatter_plot(data, x_field, y_field, title=title)
        elif chart_type == "timeline":
            return self.generate_timeline(data, x_field, y_field, title=title)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")
