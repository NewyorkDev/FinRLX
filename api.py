#!/opt/homebrew/bin/python3.12
"""
System X FastAPI - Modular Web API Layer
Production-grade API with WebSocket streaming and Redis communication

Features:
- Real-time WebSocket streaming for portfolio data
- Emergency stop controls via Redis pub/sub
- Horizontal scaling with multiple workers
- Automatic OpenAPI documentation
- Redis-based metrics consumption
- Clean separation from trading logic
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager

import redis
# Remove aioredis due to compatibility issues
# import aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
import uvicorn

# Load environment variables
from dotenv import load_dotenv
load_dotenv('/Users/francisclase/FinRLX/the_end/.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class EmergencyStopRequest(BaseModel):
    reason: str = "MANUAL_API_STOP"
    details: Optional[str] = None

class ConfigUpdateRequest(BaseModel):
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    trading_enabled: Optional[bool] = None
    max_position_size: Optional[float] = None

class StockAnalysisRequest(BaseModel):
    ticker: str
    include_ml: Optional[bool] = True
    include_technical: Optional[bool] = True

# Global Redis connections
redis_client: Optional[redis.Redis] = None

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.metrics_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Remaining connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")

    async def broadcast(self, message: str):
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def start_metrics_streaming(self):
        """Start background task to stream metrics from Redis"""
        if self.metrics_task and not self.metrics_task.done():
            return
        
        self.metrics_task = asyncio.create_task(self._stream_metrics())

    async def stop_metrics_streaming(self):
        """Stop metrics streaming task"""
        if self.metrics_task and not self.metrics_task.done():
            self.metrics_task.cancel()

    async def _stream_metrics(self):
        """Background task to stream real-time metrics"""
        try:
            while True:
                if not self.active_connections:
                    await asyncio.sleep(1)
                    continue
                
                # Get latest metrics from Redis
                try:
                    if redis_client:
                        metrics_data = redis_client.get("systemx:metrics")
                        if metrics_data:
                            metrics = json.loads(metrics_data)
                            
                            # Add timestamp
                            metrics['stream_timestamp'] = datetime.now().isoformat()
                            
                            # Broadcast to all connected clients
                            await self.broadcast(json.dumps({
                                'type': 'metrics_update',
                                'data': metrics
                            }))
                
                except Exception as e:
                    logger.error(f"Error streaming metrics: {e}")
                
                await asyncio.sleep(2)  # Stream every 2 seconds
                
        except asyncio.CancelledError:
            logger.info("Metrics streaming task cancelled")
        except Exception as e:
            logger.error(f"Metrics streaming error: {e}")

# Initialize connection manager
manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Startup
    await setup_redis_connections()
    await manager.start_metrics_streaming()
    
    # Start background monitoring
    monitor_task = asyncio.create_task(monitor_system_health())
    
    logger.info("🚀 System X API started successfully")
    
    yield
    
    # Shutdown
    monitor_task.cancel()
    await manager.stop_metrics_streaming()
    if redis_client:
        redis_client.close()
    logger.info("🛑 System X API shutdown complete")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="System X Trading API",
    description="Production-grade autonomous trading system API with real-time WebSocket streaming",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

async def setup_redis_connections():
    """Setup Redis connections"""
    global redis_client
    
    try:
        # Redis configuration from environment
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        redis_ssl = os.getenv('REDIS_SSL', 'false').lower() == 'true'
        
        # Synchronous Redis client
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_password,
            ssl=redis_ssl,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        
        # Test synchronous connection
        redis_client.ping()
        
        logger.info(f"✅ Redis connected to {redis_host}:{redis_port}")
        
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        # Fallback to local Redis for development
        try:
            redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
            redis_client.ping()
            logger.info("✅ Connected to local Redis fallback")
        except Exception as fallback_error:
            logger.error(f"❌ Local Redis fallback failed: {fallback_error}")
            redis_client = None

# Dashboard routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main trading dashboard"""
    try:
        return templates.TemplateResponse("dashboard.html", {"request": request})
    except Exception as e:
        logger.error(f"Main dashboard error: {e}")
        return templates.TemplateResponse("simple_dashboard.html", {"request": request})

@app.get("/simple", response_class=HTMLResponse)
async def simple_dashboard(request: Request):
    """Simple fallback dashboard"""
    return templates.TemplateResponse("simple_dashboard.html", {"request": request})

# WebSocket endpoint for real-time streaming
@app.websocket("/ws/portfolio")
async def websocket_portfolio(websocket: WebSocket):
    """Real-time portfolio data streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle client messages
            data = await websocket.receive_text()
            
            # Handle client commands
            try:
                message = json.loads(data)
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({'type': 'pong', 'timestamp': datetime.now().isoformat()}))
                elif message.get('type') == 'request_metrics':
                    # Send latest metrics immediately
                    if redis_client:
                        metrics_data = redis_client.get("systemx:metrics")
                        if metrics_data:
                            await websocket.send_text(json.dumps({
                                'type': 'metrics_update',
                                'data': json.loads(metrics_data)
                            }))
            except json.JSONDecodeError:
                # Handle non-JSON messages (keep-alive, etc.)
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# API Endpoints
@app.get("/health")
async def health_check():
    """System health check"""
    try:
        if redis_client:
            health_data = redis_client.get("systemx:health")
            if health_data:
                return json.loads(health_data)
        
        # Fallback health check
        return {
            "status": "API_OPERATIONAL",
            "timestamp": datetime.now().isoformat(),
            "redis_connected": redis_client is not None,
            "api_version": "2.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "DEGRADED", "error": str(e)}
        )

@app.get("/metrics")
async def get_metrics():
    """Get current trading metrics"""
    try:
        if redis_client:
            metrics_data = redis_client.get("systemx:metrics")
            if metrics_data:
                return json.loads(metrics_data)
        
        # Fallback metrics
        return {
            "performance": {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "var_95": 0.0
            },
            "trading": {
                "trades_today": 0,
                "positions": 0,
                "exposure": 0.0,
                "trading_enabled": True
            },
            "ml_model": {"available": False},
            "strategy_performance": {},
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/qualified-stocks")
async def get_qualified_stocks():
    """Get V9B qualified stocks"""
    try:
        if redis_client:
            stocks_data = redis_client.get("systemx:qualified_stocks")
            if stocks_data:
                return json.loads(stocks_data)
        
        # Fallback
        return []
        
    except Exception as e:
        logger.error(f"Qualified stocks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/live-data")
async def get_live_data():
    """Get real-time trading data"""
    try:
        if redis_client:
            live_data = redis_client.get("systemx:live_data")
            if live_data:
                return json.loads(live_data)
        
        # Fallback
        return {
            "timestamp": datetime.now().isoformat(),
            "account_equity": 30000,
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "positions": {},
            "trading_signals": {},
            "market_open": False
        }
        
    except Exception as e:
        logger.error(f"Live data error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze-stock")
async def analyze_stock(ticker: str):
    """Analyze a specific stock"""
    try:
        if redis_client:
            # Request analysis from system_x via Redis
            analysis_request = {
                "ticker": ticker,
                "timestamp": datetime.now().isoformat(),
                "request_id": f"api_{datetime.now().strftime('%H%M%S')}"
            }
            
            redis_client.setex(f"systemx:analysis_request:{ticker}", 300, json.dumps(analysis_request))
            
            # Wait for analysis response (with timeout)
            for attempt in range(10):  # 10 seconds timeout
                response_data = redis_client.get(f"systemx:analysis_response:{ticker}")
                if response_data:
                    redis_client.delete(f"systemx:analysis_response:{ticker}")
                    return json.loads(response_data)
                await asyncio.sleep(1)
            
            # Timeout - return basic analysis
            return {
                "ticker": ticker,
                "dts_score": "Pending",
                "v9b_confidence": "Analyzing",
                "ml_signal": "Processing",
                "current_price": "N/A",
                "recommendation": "HOLD",
                "risk_level": "MEDIUM",
                "claude_analysis": "Analysis request timed out. System may be processing backlog.",
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            # Fallback analysis
            return {
                "ticker": ticker,
                "dts_score": "N/A",
                "v9b_confidence": "N/A", 
                "ml_signal": "N/A",
                "current_price": "N/A",
                "recommendation": "HOLD",
                "risk_level": "MEDIUM",
                "claude_analysis": "Redis not available - cannot perform real-time analysis",
                "timestamp": datetime.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"Stock analysis error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """Emergency stop via Redis command"""
    try:
        if redis_client:
            # Send emergency stop command via Redis pub/sub
            stop_command = {
                "command": "EMERGENCY_STOP",
                "reason": request.reason,
                "details": request.details or "API emergency stop request",
                "timestamp": datetime.now().isoformat(),
                "source": "API"
            }
            
            redis_client.publish("systemx:commands", json.dumps(stop_command))
            
            # Also set direct command in Redis
            redis_client.setex("systemx:emergency_stop", 60, json.dumps(stop_command))
            
            logger.info(f"Emergency stop command sent: {request.reason}")
            return {"status": "emergency_stop_initiated", "reason": request.reason}
        
        else:
            logger.error("Emergency stop failed - Redis not available")
            raise HTTPException(status_code=503, detail="Redis not available")
        
    except Exception as e:
        logger.error(f"Emergency stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config():
    """Get current system configuration"""
    try:
        if redis_client:
            config_data = redis_client.get("systemx:config")
            if config_data:
                return json.loads(config_data)
        
        # Fallback config
        return {
            "max_position_size": 0.15,
            "max_total_exposure": 0.75,
            "stop_loss_pct": 0.05,
            "take_profit_pct": 0.10,
            "kelly_enabled": True,
            "trading_enabled": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Config get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config")
async def update_config(config: ConfigUpdateRequest):
    """Update system configuration"""
    try:
        if redis_client:
            # Send config update command
            config_update = {
                "command": "UPDATE_CONFIG",
                "updates": config.dict(exclude_unset=True),
                "timestamp": datetime.now().isoformat(),
                "source": "API"
            }
            
            redis_client.publish("systemx:commands", json.dumps(config_update))
            redis_client.setex("systemx:config_update", 60, json.dumps(config_update))
            
            return {"status": "config_update_sent", "updates": config.dict(exclude_unset=True)}
        
        else:
            raise HTTPException(status_code=503, detail="Redis not available")
        
    except Exception as e:
        logger.error(f"Config update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts")
async def get_account_status():
    """Get status of all 3 trading accounts"""
    try:
        if redis_client:
            accounts_data = redis_client.get("systemx:accounts")
            if accounts_data:
                return json.loads(accounts_data)
        
        # Fallback
        return {
            "accounts": [
                {"name": "PRIMARY_30K", "balance": 30000, "status": "ACTIVE"},
                {"name": "SECONDARY_30K", "balance": 30000, "status": "ACTIVE"},
                {"name": "TERTIARY_30K", "balance": 30000, "status": "ACTIVE"}
            ],
            "total_balance": 90000,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Accounts error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task to monitor system health
async def monitor_system_health():
    """Background task to monitor trading system health"""
    while True:
        try:
            if redis_client:
                # Check if system_x is publishing metrics
                last_metrics = redis_client.get("systemx:metrics")
                if last_metrics:
                    metrics = json.loads(last_metrics)
                    metrics_age = datetime.now() - datetime.fromisoformat(metrics.get('timestamp', datetime.now().isoformat()))
                    
                    if metrics_age.total_seconds() > 300:  # 5 minutes
                        logger.warning("System X metrics are stale - trading system may be down")
                
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
        
        await asyncio.sleep(60)  # Check every minute

# Background task added to lifespan context manager above

if __name__ == "__main__":
    # Run with uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8080,
        workers=2,  # Multiple workers for horizontal scaling
        access_log=True,
        log_level="info",
        reload=False  # Set to True for development
    )