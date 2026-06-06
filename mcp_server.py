from fastapi import FastAPI, HTTPException, Header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os
from datetime import datetime
from typing import Optional, List

app = FastAPI()

# SMTP Configuration from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "mail.infomaniak.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "info@gmc-works.com")
SMTP_PASS = os.getenv("SMTP_PASS", "eK2MSV%K&vje-&$2")
SMTP_FROM = os.getenv("SMTP_FROM", "info@gmc-works.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "GMC Daily Picks")

# Send-list (recipients) - from environment variable (JSON string)
SEND_LIST_JSON = os.getenv("SEND_LIST", '["your-email@example.com"]')
try:
    SEND_LIST = json.loads(SEND_LIST_JSON)
except json.JSONDecodeError:
    SEND_LIST = ["your-email@example.com"]

# API authentication token
SECRET_TOKEN = os.getenv("SECRET_TOKEN", "default-token-change-me")

def format_analysis_html(data: dict) -> str:
    """
    Format market analysis into beautiful HTML email
    """
    stocks = data.get("stocks", [])
    summary = data.get("summary", "No summary provided")
    analysis_date = data.get("analysis_date", "N/A")
    additional_notes = data.get("additional_notes", "")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .header p {{
                margin: 10px 0 0 0;
                font-size: 14px;
                opacity: 0.9;
            }}
            .content {{
                padding: 30px;
            }}
            .summary {{
                background-color: #f0f4ff;
                border-left: 4px solid #667eea;
                padding: 15px;
                margin-bottom: 20px;
                border-radius: 4px;
            }}
            .summary p {{
                margin: 0;
                color: #333;
                font-size: 16px;
            }}
            .stocks {{
                margin: 20px 0;
            }}
            .stock-item {{
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 15px;
                margin-bottom: 15px;
            }}
            .stock-item:hover {{
                background-color: #f5f5f5;
                border-color: #667eea;
            }}
            .ticker {{
                font-size: 18px;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 8px;
            }}
            .price {{
                font-size: 16px;
                color: #333;
                margin: 5px 0;
            }}
            .signal {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                margin: 8px 0;
            }}
            .signal.buy {{
                background-color: #d4edda;
                color: #155724;
            }}
            .signal.sell {{
                background-color: #f8d7da;
                color: #721c24;
            }}
            .signal.hold {{
                background-color: #fff3cd;
                color: #856404;
            }}
            .reason {{
                font-size: 14px;
                color: #555;
                margin-top: 8px;
                font-style: italic;
                padding-top: 8px;
                border-top: 1px solid #e0e0e0;
            }}
            .footer {{
                background-color: #f5f5f5;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
                border-top: 1px solid #e0e0e0;
            }}
            .timestamp {{
                color: #999;
                font-size: 11px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 Daily Market Analysis</h1>
                <p>{analysis_date}</p>
            </div>
            <div class="content">
                <div class="summary">
                    <p><strong>📈 Summary:</strong> {summary}</p>
                </div>
    """
    
    # Add each stock
    if stocks:
        html += '<div class="stocks">'
        for stock in stocks:
            ticker = stock.get('ticker', 'N/A')
            price = stock.get('price', 'N/A')
            signal = str(stock.get('signal', 'HOLD')).upper()
            reason = stock.get('reason', 'No details')
            volume = stock.get('volume', 'N/A')
            change = stock.get('change', 'N/A')
            
            signal_class = signal.lower() if signal.lower() in ['buy', 'sell', 'hold'] else 'hold'
            
            html += f"""
            <div class="stock-item">
                <div class="ticker">🔹 {ticker}</div>
                <div class="price">Price: <strong>${price}</strong></div>
                <div class="price">Volume: <strong>{volume}</strong></div>
                <div class="price">Change: <strong>{change}</strong></div>
                <span class="signal {signal_class}">{signal}</span>
                <div class="reason">💡 {reason}</div>
            </div>
            """
        html += '</div>'
    
    # Add additional notes if provided
    if additional_notes:
        html += f"""
        <div class="summary" style="margin-top: 20px;">
            <p><strong>📝 Notes:</strong> {additional_notes}</p>
        </div>
        """
    
    html += f"""
            </div>
            <div class="footer">
                <p>Generated by GMC Daily Picks • {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p class="timestamp">Automated market analysis powered by Claude</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def send_email(html_content: str, subject: str = "Daily Market Analysis") -> dict:
    """
    Send formatted HTML email to all recipients in SEND_LIST
    """
    success_count = 0
    failed_recipients = []
    
    try:
        for recipient in SEND_LIST:
            try:
                # Create message for each recipient
                msg = MIMEMultipart('alternative')
                msg['Subject'] = subject
                msg['From'] = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
                msg['To'] = recipient
                
                # Attach HTML content
                msg.attach(MIMEText(html_content, 'html'))
                
                # Connect to SMTP server
                server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                
                # Send email
                server.sendmail(SMTP_FROM, recipient, msg.as_string())
                server.quit()
                
                success_count += 1
            except Exception as e:
                failed_recipients.append({
                    "email": recipient,
                    "error": str(e)
                })
        
        return {
            "status": "success" if success_count > 0 else "error",
            "emails_sent": success_count,
            "total_recipients": len(SEND_LIST),
            "failed": failed_recipients
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"SMTP error: {str(e)}",
            "failed": SEND_LIST
        }

# ============ API ENDPOINTS ============

@app.get("/health")
def health_check():
    """Health check - verify service is running"""
    return {
        "status": "healthy",
        "service": "financial-analysis-mcp",
        "smtp_configured": bool(SMTP_USER),
        "send_list_count": len(SEND_LIST),
        "ready": True
    }

@app.get("/config")
def get_config(authorization: Optional[str] = Header(None)):
    """View current configuration (requires auth token)"""
    expected_auth = f"Bearer {SECRET_TOKEN}"
    if authorization != expected_auth:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "smtp_host": SMTP_HOST,
        "smtp_port": SMTP_PORT,
        "smtp_user": SMTP_USER,
        "smtp_from": SMTP_FROM,
        "smtp_from_name": SMTP_FROM_NAME,
        "send_list": SEND_LIST,
        "send_list_count": len(SEND_LIST)
    }

@app.post("/receive-analysis")
def receive_analysis(
    data: dict,
    authorization: Optional[str] = Header(None)
):
    """
    Main endpoint: Receive Claude market analysis and send formatted email
    
    Expected header: Authorization: Bearer {SECRET_TOKEN}
    Expected body: JSON with stocks, summary, analysis_date, optional additional_notes
    """
    
    # Validate authorization token
    expected_auth = f"Bearer {SECRET_TOKEN}"
    if authorization != expected_auth:
        raise HTTPException(status_code=401, detail="Unauthorized - invalid or missing token")
    
    # Validate required fields
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Body must be JSON object")
    
    if "stocks" not in data or "summary" not in data or "analysis_date" not in data:
        raise HTTPException(
            status_code=400, 
            detail="Missing required fields: stocks, summary, analysis_date"
        )
    
    try:
        # Format analysis as HTML email
        html_content = format_analysis_html(data)
        
        # Send email to all recipients
        email_result = send_email(
            html_content,
            subject=f"Daily Market Analysis - {data.get('analysis_date', 'N/A')}"
        )
        
        return {
            "status": "success",
            "message": "Analysis processed and emails sent",
            "email_result": email_result,
            "received_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process analysis: {str(e)}"
        )

@app.get("/send-list")
def get_send_list(authorization: Optional[str] = Header(None)):
    """View current send-list (requires auth)"""
    expected_auth = f"Bearer {SECRET_TOKEN}"
    if authorization != expected_auth:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return {
        "send_list": SEND_LIST,
        "total_recipients": len(SEND_LIST)
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)