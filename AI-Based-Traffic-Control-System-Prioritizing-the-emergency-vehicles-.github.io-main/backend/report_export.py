"""
report_export.py — PDF and advanced report generation
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io
import os
from datetime import datetime


class ReportExporter:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom styles for cyberpunk theme"""
        self.styles.add(ParagraphStyle(
            name='CyberTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#00ff88'),
            alignment=TA_CENTER,
            spaceAfter=30,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CyberHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#00aaff'),
            spaceAfter=10,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CyberNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#c8d8e8'),
            fontName='Helvetica'
        ))
    
    def generate_pdf_report(self, data: dict) -> bytes:
        """Generate PDF report from analytics data"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            title="Traffic Analytics Report"
        )
        
        story = []
        
        # Title
        story.append(Paragraph("AI SMART TRAFFIC CONTROL SYSTEM", self.styles['CyberTitle']))
        story.append(Paragraph(f"Analytics Report", self.styles['CyberTitle']))
        story.append(Paragraph(f"Generated: {data['last_updated']}", self.styles['CyberNormal']))
        story.append(Spacer(1, 0.5 * inch))
        
        # Summary Section
        story.append(Paragraph("EXECUTIVE SUMMARY", self.styles['CyberHeading']))
        story.append(Spacer(1, 0.1 * inch))
        
        summary_data = [
            ["Metric", "Value"],
            ["Total Vehicles Detected", str(data['total_vehicles'])],
            ["Emergency Vehicles", str(data['emergency_count'])],
            ["Emergency Overrides", str(data['emergency_overrides'])],
            ["Average Waiting Time", f"{data['avg_waiting_time']} seconds"],
            ["Signal Efficiency", f"{data['signal_efficiency']}%"],
            ["Average Green Duration", f"{data['avg_green_duration']} seconds"],
        ]
        
        summary_table = Table(summary_data, colWidths=[3 * inch, 2 * inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00ff88')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111520')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#c8d8e8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2a3a')),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Vehicle Type Breakdown
        story.append(Paragraph("VEHICLE TYPE BREAKDOWN", self.styles['CyberHeading']))
        story.append(Spacer(1, 0.1 * inch))
        
        vehicle_data = [["Vehicle Type", "Count"]]
        for vtype, count in data['vehicle_types'].items():
            vehicle_data.append([vtype.capitalize(), str(count)])
        
        vehicle_table = Table(vehicle_data, colWidths=[3 * inch, 2 * inch])
        vehicle_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00aaff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111520')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#c8d8e8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2a3a')),
        ]))
        story.append(vehicle_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Camera Statistics
        story.append(Paragraph("CAMERA STATISTICS", self.styles['CyberHeading']))
        story.append(Spacer(1, 0.1 * inch))
        
        camera_data = [["Camera", "Vehicle Count", "Density", "Congestion", "Wait Time"]]
        for cam in data['cameras']:
            camera_data.append([
                cam['name'],
                str(cam['count']),
                f"{cam['density']}%",
                cam['congestion'],
                f"{cam['waiting_time']}s"
            ])
        
        camera_table = Table(camera_data, colWidths=[1.2 * inch] * 5)
        camera_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff3355')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111520')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#c8d8e8')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2a3a')),
        ]))
        story.append(camera_table)
        story.append(Spacer(1, 0.3 * inch))
        
        # Peak Hours
        if data['peak_hours']:
            story.append(Paragraph("PEAK TRAFFIC HOURS", self.styles['CyberHeading']))
            story.append(Spacer(1, 0.1 * inch))
            
            peak_data = [["Hour", "Traffic Density"]]
            for peak in data['peak_hours']:
                peak_data.append([peak['hour'], f"{peak['density']} vehicles/min"])
            
            peak_table = Table(peak_data, colWidths=[2.5 * inch, 2.5 * inch])
            peak_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffcc00')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111520')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2a3a')),
            ]))
            story.append(peak_table)
            story.append(Spacer(1, 0.3 * inch))
        
        # Emergency Logs
        if data['emergency_logs']:
            story.append(Paragraph("EMERGENCY VEHICLE LOGS", self.styles['CyberHeading']))
            story.append(Spacer(1, 0.1 * inch))
            
            emergency_data = [["Time", "Camera", "Type", "ETA", "Priority"]]
            for log in data['emergency_logs'][:10]:
                emergency_data.append([
                    log['timestamp'],
                    log['camera'],
                    log['vehicle_type'],
                    f"{log['eta']}s",
                    log['signal_priority']
                ])
            
            emergency_table = Table(emergency_data, colWidths=[1.2 * inch] * 5)
            emergency_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff3355')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#111520')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#c8d8e8')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e2a3a')),
            ]))
            story.append(emergency_table)
            story.append(Spacer(1, 0.3 * inch))
        
        # Recommendations
        story.append(Paragraph("SMART RECOMMENDATIONS", self.styles['CyberHeading']))
        story.append(Spacer(1, 0.1 * inch))
        
        for rec in data.get('recommendations', []):
            story.append(Paragraph(f"• {rec}", self.styles['CyberNormal']))
            story.append(Spacer(1, 0.05 * inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer.getvalue()