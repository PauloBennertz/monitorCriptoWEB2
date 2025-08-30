# robust_services.py

import time
import json
import hashlib
import logging
import pandas as pd
import requests
from collections import deque
from threading import Lock
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

# ==========================================
# 1. RATE LIMITING
# ==========================================
class BinanceRateLimiter:
    def __init__(self):
        self.requests_1min = deque()
        self.requests_5min = deque()
        self.lock = Lock()
        # Limites mais conservadores para evitar bloqueios
        self.limit_1min = 800  # Reduzido de 1000 para 800
        self.limit_5min = 4000  # Reduzido de 5000 para 4000
        self.manual_update_mode = False
    
    def wait_if_needed(self):
        with self.lock:
            now = time.time()
            while self.requests_1min and now - self.requests_1min[0] > 60: self.requests_1min.popleft()
            while self.requests_5min and now - self.requests_5min[0] > 300: self.requests_5min.popleft()
            
            # Se estiver em modo de atualização manual, usa limites mais conservadores
            current_limit_1min = self.limit_1min // 2 if self.manual_update_mode else self.limit_1min
            current_limit_5min = self.limit_5min // 2 if self.manual_update_mode else self.limit_5min
            
            if len(self.requests_1min) >= current_limit_1min:
                sleep_time = 60 - (now - self.requests_1min[0])
                if sleep_time > 0:
                    print(f"LOG: Rate limit 1min atingido. Aguardando {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
            
            if len(self.requests_5min) >= current_limit_5min:
                sleep_time = 300 - (now - self.requests_5min[0])
                if sleep_time > 0:
                    print(f"LOG: Rate limit 5min atingido. Aguardando {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
            
            self.requests_1min.append(time.time())
            self.requests_5min.append(time.time())
    
    def set_manual_update_mode(self, enabled: bool):
        """Ativa/desativa modo de atualização manual com limites mais conservadores."""
        with self.lock:
            self.manual_update_mode = enabled
            if enabled:
                print("LOG: Modo de atualização manual ativado (limites reduzidos)")
            else:
                print("LOG: Modo de atualização manual desativado")
    
    def get_current_usage(self):
        """Retorna o uso atual das APIs em porcentagem."""
        with self.lock:
            now = time.time()
            # Limpa requisições antigas
            while self.requests_1min and now - self.requests_1min[0] > 60: 
                self.requests_1min.popleft()
            while self.requests_5min and now - self.requests_5min[0] > 300: 
                self.requests_5min.popleft()
            
            # Calcula porcentagens
            current_limit_1min = self.limit_1min // 2 if self.manual_update_mode else self.limit_1min
            current_limit_5min = self.limit_5min // 2 if self.manual_update_mode else self.limit_5min
            
            usage_1min = (len(self.requests_1min) / current_limit_1min) * 100
            usage_5min = (len(self.requests_5min) / current_limit_5min) * 100
            
            return {
                '1min': min(usage_1min, 100),
                '5min': min(usage_5min, 100),
                'requests_1min': len(self.requests_1min),
                'requests_5min': len(self.requests_5min),
                'limit_1min': current_limit_1min,
                'limit_5min': current_limit_5min
            }
    
    def can_perform_manual_update(self):
        """Verifica se é seguro realizar uma atualização manual."""
        usage = self.get_current_usage()
        
        # Critérios de segurança
        max_safe_usage = 70  # Máximo 70% de uso antes de bloquear
        
        if usage['1min'] > max_safe_usage:
            return False, f"Limite 1min muito alto: {usage['1min']:.1f}%"
        
        if usage['5min'] > max_safe_usage:
            return False, f"Limite 5min muito alto: {usage['5min']:.1f}%"
        
        return True, f"Seguro para atualização (1min: {usage['1min']:.1f}%, 5min: {usage['5min']:.1f}%)"

rate_limiter = BinanceRateLimiter()

# ==========================================
# 2. CACHE DE DADOS
# ==========================================
@dataclass
class CachedData:
    data: Any
    timestamp: float

class DataCache:
    def __init__(self, default_ttl=300):
        self.cache: Dict[str, CachedData] = {}
        self.default_ttl = default_ttl
        self.lock = Lock()
    
    def _generate_key(self, *args, **kwargs) -> str:
        key_data = {"args": args, "kwargs": sorted(kwargs.items())}
        key_str = json.dumps(key_data)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key_args, ttl: Optional[int] = None) -> Optional[Any]:
        if ttl is None: ttl = self.default_ttl
        key = self._generate_key(**key_args)
        with self.lock:
            if key not in self.cache: return None
            cached = self.cache[key]
            if time.time() - cached.timestamp > ttl:
                del self.cache[key]
                return None
            print(f"LOG: Cache HIT para {key_args}")
            return cached.data
    
    def set(self, key_args, data: Any):
        key = self._generate_key(**key_args)
        with self.lock:
            self.cache[key] = CachedData(data=data, timestamp=time.time())
            print(f"LOG: Cache SET para {key_args}")

data_cache = DataCache()

# ==========================================
# 3. VALIDAÇÃO ROBUSTA
# ==========================================
class DataValidator:
    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        try:
            if value is None: return default
            return float(value)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def safe_price(value: Any, default: float = 0.0) -> float:
        price = DataValidator.safe_float(value, default)
        return price if price >= 0 else default
        
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        return isinstance(symbol, str) and symbol.endswith('USDT') and len(symbol) > 4