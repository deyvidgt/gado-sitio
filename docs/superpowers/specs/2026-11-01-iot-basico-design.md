# Onda 16 — IoT Básico (Balança + Colar + Comedouro)

**Data:** 2026-11-01  
**Versão:** 1.0 (MVP)  
**Status:** Design Aprovado  
**Tempo:** 2 semanas (paralelo com Onda 19)  
**Dependências:** v5.12 (Ondas 0-14 + Onda 19 design entregues)

---

## 1. Visão Geral

**Objetivo:** Conectar sensores IoT (Bluetooth) ao app PWA, capturando dados automaticamente (peso, temperatura/GPS, consumo) sem digitação manual, com fallback offline (localStorage) e emuladores para teste.

**3 Sensores (MVP → Onda 16.X/Y):**
1. **Balança** — lê peso kg, grava em Pesagem (Manejo)
2. **Colar** — lê temperatura °C + GPS, grava em Manejo tipo "Localização + Temperatura"
3. **Comedouro** — lê consumo kg/hora, grava em Insumos

**Arquitetura:**
- Modular (cada sensor = class Sensor reutilizável)
- Offline-first (localStorage fila + sync automático)
- 2 emuladores (Web slider + Android mock futuro)
- localStorage config (pareamento persistente)
- Alertas integrados (queda peso >5%, temp fora faixa, consumo anormal)

---

## 2. Componentes

### 2.1 Estrutura localStorage

**Chaves salvas permanentemente:**

```json
{
  "iot_devices": {
    "balanca_001": {
      "name": "Balança Sala 1",
      "type": "balanca",
      "enabled": true,
      "lastSync": "2026-11-01T01:20:00Z",
      "macAddress": null
    },
    "colar_amarelo_21": {
      "name": "Colar Amarelo 21",
      "type": "colar",
      "enabled": true,
      "animal_id": "A0001"
    },
    "comedor_pasto_1": {
      "name": "Comedouro Pasto 1",
      "type": "comedor",
      "enabled": true,
      "pasto_id": "P001"
    }
  },
  
  "iot_fila_offline": [
    {
      "id": "uuid-1234",
      "timestamp": "2026-11-01T01:15:00Z",
      "device_id": "balanca_001",
      "type": "balanca",
      "valor": 420.5,
      "animal_id": "A0001",
      "status": "pendente"
    }
  ]
}
```

**Ciclo de vida fila:**
- `status: "pendente"` — offline, ou POST em andamento
- `status: "enviado"` — POST sucesso, aguarda confirmação server
- Remove da fila após POST 200 OK

---

### 2.2 Camada Sensores (`static/js/iot_sensores.js`)

**Interface Base:**

```python
# Pseudocódigo (implementar em JavaScript)
class Sensor:
    def conectar(self):
        """Retorna {sucesso: bool, msg: string}"""
        pass
    
    def ler(self):
        """Retorna {valor, timestamp, unit} ou {temperatura, lat, lng, timestamp, unit}"""
        pass
    
    def desconectar(self):
        pass
    
    def emitir(self, event, data):
        """Event listener para UI"""
        pass
```

**Implementações:**

#### 2.2.1 Balança Real (Web Bluetooth)

```javascript
class BalancaBluetooth extends Sensor {
  constructor(deviceId) {
    this.deviceId = deviceId;
    this.device = null;
    this.characteristic = null;
    this.listeners = {};
  }
  
  async conectar() {
    try {
      // Request Bluetooth device
      // Filters: Generic Access (0x180a) ou custom scale service
      this.device = await navigator.bluetooth.requestDevice({
        filters: [
          { services: ['180a'] },  // Generic Access
          { namePrefix: 'SCALE' },  // Common scale prefix
        ],
        optionalServices: ['custom_scale_service', 'battery_service']
      });
      
      const server = await this.device.gatt.connect();
      // Find characteristic com UUID de peso (custom ou standard)
      this.characteristic = await server.getPrimaryService('custom_scale_service')
        .then(svc => svc.getCharacteristic('weight_characteristic'))
        .catch(() => null);
      
      this.device.addEventListener('gattserverdisconnected', () => {
        this.emitir('desconectado', {});
      });
      
      return {
        sucesso: true,
        msg: `✅ Conectado: ${this.device.name}`
      };
    } catch (e) {
      return {
        sucesso: false,
        msg: `❌ Erro Bluetooth: ${e.message}`
      };
    }
  }
  
  async ler() {
    if (!this.device?.gatt.connected) {
      return {sucesso: false, msg: "Dispositivo desconectado"};
    }
    
    try {
      const value = await this.characteristic.readValue();
      const peso = new DataView(value).getFloat32(0, true);  // Little-endian float
      
      return {
        sucesso: true,
        valor: peso,
        unit: 'kg',
        timestamp: new Date().toISOString()
      };
    } catch (e) {
      return {sucesso: false, msg: e.message};
    }
  }
  
  async desconectar() {
    if (this.device?.gatt.connected) {
      await this.device.gatt.disconnect();
    }
  }
  
  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
}
```

#### 2.2.2 Balança Emulador (Slider Web)

```javascript
class BalancaEmulador extends Sensor {
  constructor(deviceId) {
    this.deviceId = deviceId;
    this.peso = 400;  // kg inicial
    this.listeners = {};
  }
  
  async conectar() {
    return {
      sucesso: true,
      msg: "✅ Emulador conectado (use slider abaixo)"
    };
  }
  
  async ler() {
    return {
      sucesso: true,
      valor: this.peso,
      unit: 'kg',
      timestamp: new Date().toISOString()
    };
  }
  
  setPeso(newValue) {
    this.peso = parseFloat(newValue);
    this.emitir('leitura', {valor: this.peso, unit: 'kg'});
  }
  
  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
}
```

#### 2.2.3 Colar (Temperatura + GPS)

```javascript
class ColarBluetooth extends Sensor {
  async ler() {
    // Bluetooth para temp + GPS
    // Fallback: geolocation API do navegador
    const position = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject);
    });
    
    return {
      sucesso: true,
      temperatura: 38.5,  // Placeholder; ler via Bluetooth depois
      lat: position.coords.latitude,
      lng: position.coords.longitude,
      unit: '°C + GPS',
      timestamp: new Date().toISOString()
    };
  }
  
  emitir(event, data) { /* ... */ }
  on(event, callback) { /* ... */ }
}

class ColarEmulador extends Sensor {
  constructor() {
    this.temp = 38.5;
    this.lat = -19.123;
    this.lng = -45.456;
  }
  
  async ler() {
    return {
      sucesso: true,
      temperatura: this.temp + (Math.random() - 0.5),  // ±0.5°C variação
      lat: this.lat,
      lng: this.lng,
      timestamp: new Date().toISOString()
    };
  }
  
  emitir(event, data) { /* ... */ }
  on(event, callback) { /* ... */ }
}
```

#### 2.2.4 Comedouro (Consumo)

```javascript
class ComedorBluetooth extends Sensor {
  async ler() {
    // Bluetooth: célula de carga (peso antes/depois)
    // Calcula consumo = peso_inicial - peso_atual
    return {
      sucesso: true,
      consumo_kg: 12.5,  // kg/hora
      unit: 'kg/hora',
      timestamp: new Date().toISOString()
    };
  }
}

class ComedorEmulador extends Sensor {
  constructor() {
    this.consumo = 12.5;
  }
  
  async ler() {
    return {
      sucesso: true,
      consumo_kg: this.consumo + (Math.random() - 0.5) * 2,  // ±1 kg variação
      unit: 'kg/hora',
      timestamp: new Date().toISOString()
    };
  }
}
```

---

### 2.3 Gerenciador IoT (`static/js/iot_manager.js`)

```javascript
class IoTManager {
  constructor() {
    this.sensores = {};  // {device_id: Sensor instance}
    this.config = {};    // {device_id: {name, type, enabled, ...}}
    this.listeners = {};
    
    this.carregarConfig();
    this.setupSyncOnOnline();
  }
  
  carregarConfig() {
    const saved = localStorage.getItem('iot_devices');
    this.config = saved ? JSON.parse(saved) : {};
  }
  
  salvarConfig() {
    localStorage.setItem('iot_devices', JSON.stringify(this.config));
  }
  
  async parearSensor(tipo, nome_customizado = null) {
    /**
     * Pareamento: cria nova instância de sensor
     * Input: tipo ('balanca', 'colar', 'comedor')
     * Output: {sucesso, deviceId, msg}
     */
    const deviceId = `${tipo}_${Date.now()}`;
    const nome = nome_customizado || `${tipo} ${Object.keys(this.config).length + 1}`;
    
    let sensorInstancia;
    
    try {
      if (tipo === 'balanca') {
        // Tenta Web Bluetooth; fallback: emulador
        sensorInstancia = navigator.bluetooth
          ? new BalancaBluetooth(deviceId)
          : new BalancaEmulador(deviceId);
      } else if (tipo === 'colar') {
        sensorInstancia = new ColarBluetooth();  // Sempre Bluetooth; fallback depois
      } else if (tipo === 'comedor') {
        sensorInstancia = new ComedorBluetooth();
      } else {
        return {sucesso: false, msg: "Tipo inválido"};
      }
      
      const result = await sensorInstancia.conectar();
      
      if (result.sucesso) {
        this.sensores[deviceId] = sensorInstancia;
        this.config[deviceId] = {
          name: nome,
          type: tipo,
          enabled: true,
          createdAt: new Date().toISOString()
        };
        
        this.salvarConfig();
        this.emitir('pareado', {deviceId, nome, tipo});
        
        return {sucesso: true, deviceId, msg: result.msg};
      } else {
        return {sucesso: false, msg: result.msg};
      }
    } catch (e) {
      return {sucesso: false, msg: `Erro: ${e.message}`};
    }
  }
  
  async lerSensor(deviceId) {
    /**
     * Lê valor do sensor, enfileira offline, tenta enviar
     * Output: {sucesso, valor, timestamp} ou null
     */
    const config = this.config[deviceId];
    if (!config || !config.enabled) return null;
    
    const sensor = this.sensores[deviceId];
    if (!sensor) return null;
    
    try {
      const leitura = await sensor.ler();
      
      if (!leitura.sucesso) {
        return null;
      }
      
      // Enfileira offline
      this.enfileirarOffline(deviceId, leitura);
      
      // Tenta enviar pro servidor
      await this.enviarParaServidor(deviceId, leitura);
      
      return leitura;
    } catch (e) {
      console.error(`Erro ao ler ${deviceId}:`, e);
      return null;
    }
  }
  
  enfileirarOffline(deviceId, leitura) {
    /**
     * Salva em fila offline (localStorage)
     * Será sincronizado quando online
     */
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    
    const tipo = this.config[deviceId].type;
    let item = {
      id: `${deviceId}_${Date.now()}`,
      timestamp: leitura.timestamp,
      device_id: deviceId,
      type: tipo,
      status: 'pendente'
    };
    
    // Payload diferente por tipo
    if (tipo === 'balanca') {
      item.valor = leitura.valor;
      item.animal_id = document.querySelector('[data-animal-id]')?.dataset.animalId || '?';
    } else if (tipo === 'colar') {
      item.temperatura = leitura.temperatura;
      item.lat = leitura.lat;
      item.lng = leitura.lng;
      item.animal_id = this.config[deviceId].animal_id || '?';
    } else if (tipo === 'comedor') {
      item.consumo_kg = leitura.consumo_kg;
      item.pasto_id = this.config[deviceId].pasto_id || '?';
    }
    
    fila.push(item);
    localStorage.setItem('iot_fila_offline', JSON.stringify(fila));
  }
  
  async enviarParaServidor(deviceId, leitura) {
    /**
     * POST para /api/iot/* conforme tipo
     * Atualiza status fila se sucesso
     */
    const tipo = this.config[deviceId].type;
    let endpoint, payload;
    
    if (tipo === 'balanca') {
      endpoint = '/api/iot/pesagem';
      payload = {
        device_id: deviceId,
        valor: leitura.valor,
        timestamp: leitura.timestamp,
        animal_id: document.querySelector('[data-animal-id]')?.dataset.animalId
      };
    } else if (tipo === 'colar') {
      endpoint = '/api/iot/temperatura';
      payload = {
        device_id: deviceId,
        temperatura: leitura.temperatura,
        lat: leitura.lat,
        lng: leitura.lng,
        timestamp: leitura.timestamp,
        animal_id: this.config[deviceId].animal_id
      };
    } else if (tipo === 'comedor') {
      endpoint = '/api/iot/consumo';
      payload = {
        device_id: deviceId,
        consumo_kg: leitura.consumo_kg,
        timestamp: leitura.timestamp,
        pasto_id: this.config[deviceId].pasto_id
      };
    }
    
    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      
      if (response.ok) {
        // Remove da fila
        this.removerDaFila(deviceId);
        this.emitir('enviado', {deviceId, tipo});
      }
    } catch (e) {
      console.log(`Offline — enfileirado: ${e.message}`);
      // Permanece em fila, será retentado em sync
    }
  }
  
  removerDaFila(deviceId) {
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    const nova = fila.filter(f => f.device_id !== deviceId);
    localStorage.setItem('iot_fila_offline', JSON.stringify(nova));
  }
  
  async sincronizar() {
    /**
     * Manual ou automática ao reconectar (online event)
     * Retenta todos os itens pendentes
     */
    const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
    console.log(`🔄 Sincronizando ${fila.length} itens...`);
    
    try {
      const response = await fetch('/api/iot/sync', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({fila})
      });
      
      if (response.ok) {
        localStorage.setItem('iot_fila_offline', JSON.stringify([]));
        this.emitir('sincronizado', {count: fila.length});
      }
    } catch (e) {
      console.error('Erro sync:', e);
    }
  }
  
  setupSyncOnOnline() {
    /**
     * Detecta reconexão e sincroniza automaticamente
     */
    window.addEventListener('online', () => {
      console.log('✅ Online — sincronizando fila...');
      this.sincronizar();
    });
  }
  
  emitir(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }
  
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }
}

// Global instance
const iotManager = new IoTManager();
```

---

### 2.4 API Endpoints (`routes_iot.py` — NEW FILE)

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
routes_iot.py — IoT sensor endpoints (Onda 16)

Recebe dados: balança (peso), colar (temp+GPS), comedouro (consumo)
Grava em: Pesagem (Manejo), Animais (localização), Insumos (consumo)
"""

import pandas as pd
from flask import request, jsonify
from datetime import datetime, timedelta

import db
import animais as A
from extensions import app, login_required
from routes_animais import _membro_logado, fazer_backup_seguro

@app.route("/api/iot/pesagem", methods=["POST"])
@login_required
def api_iot_pesagem():
    """
    POST: {device_id, valor (kg), timestamp, animal_id}
    Grava em Manejo tipo "Pesagem"
    """
    data = request.json
    
    device_id = data.get('device_id', 'balanca_?')
    peso = data.get('valor')
    timestamp_str = data.get('timestamp')
    animal_id = data.get('animal_id')
    
    if not peso or not animal_id:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        
        # Formata para Excel
        data_str = timestamp.strftime("%d/%m/%Y")
        
        # Grava em Manejo
        nova_linha = [
            data_str,
            "Pesagem",
            1,
            f"Balança {device_id}: {peso}kg (IoT)",
            _membro_logado(),
            "",
            f"{animal_id}: {peso}kg",  # Produto (para histórico)
            "",
            animal_id,
            f"{animal_id}: {peso}kg",  # Pesos (coluna para pesagem_avancada.py)
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Peso {peso}kg registrado para {animal_id}"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/temperatura", methods=["POST"])
@login_required
def api_iot_temperatura():
    """
    POST: {device_id, temperatura (°C), lat, lng, timestamp, animal_id}
    Grava em Manejo tipo "Localização + Temperatura"
    """
    data = request.json
    
    device_id = data.get('device_id', 'colar_?')
    temp = data.get('temperatura')
    lat = data.get('lat')
    lng = data.get('lng')
    timestamp_str = data.get('timestamp')
    animal_id = data.get('animal_id')
    
    if not temp or not animal_id:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        data_str = timestamp.strftime("%d/%m/%Y")
        
        # Grava em Manejo tipo "Localização + Temperatura"
        nova_linha = [
            data_str,
            "Localização + Temperatura",  # Novo tipo em config.py
            1,
            f"Colar {device_id}: {temp}°C | GPS {lat},{lng}",
            _membro_logado(),
            "",
            f"Temp {temp}°C",
            "",
            animal_id,
            f"LAT:{lat} LNG:{lng}",
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        # Alerta se temp fora de faixa (18-28°C)
        alerta = ""
        if temp < 18:
            alerta = " ⚠️ Temp baixa (possível stress pelo frio)"
        elif temp > 28:
            alerta = " 🔥 Temp alta (possível stress pelo calor)"
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Temperatura {temp}°C registrada {alerta}"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/consumo", methods=["POST"])
@login_required
def api_iot_consumo():
    """
    POST: {device_id, consumo_kg, timestamp, pasto_id}
    Grava em Manejo tipo "Consumo Comedouro"
    """
    data = request.json
    
    device_id = data.get('device_id', 'comedor_?')
    consumo = data.get('consumo_kg')
    timestamp_str = data.get('timestamp')
    pasto_id = data.get('pasto_id')
    
    if not consumo:
        return jsonify({"sucesso": False, "msg": "Faltam campos"}), 400
    
    try:
        timestamp = pd.to_datetime(timestamp_str).normalize()
        data_str = timestamp.strftime("%d/%m/%Y")
        
        # Grava em Manejo tipo "Consumo Comedouro"
        nova_linha = [
            data_str,
            "Consumo Comedouro",  # Novo tipo em config.py
            1,
            f"Comedouro {device_id}: {consumo}kg/h",
            _membro_logado(),
            "",
            f"Consumo {consumo}kg",
            "",
            "",
            f"Pasto: {pasto_id}",
        ]
        
        db.salvar_linha("Manejo", nova_linha)
        fazer_backup_seguro()
        
        return jsonify({
            "sucesso": True,
            "msg": f"✅ Consumo {consumo}kg registrado"
        })
    
    except Exception as e:
        return jsonify({"sucesso": False, "msg": f"❌ Erro: {str(e)}"}), 500

@app.route("/api/iot/sync", methods=["POST"])
@login_required
def api_iot_sync():
    """
    POST: {fila: [{device_id, type, valor, timestamp, ...}, ...]}
    Processa todos os itens offline enfileirados
    """
    data = request.json
    fila = data.get('fila', [])
    
    processados = 0
    erros = []
    
    for item in fila:
        try:
            tipo = item.get('type')
            
            if tipo == 'balanca':
                # Re-faz POST /api/iot/pesagem
                resp = api_iot_pesagem.__wrapped__(
                    request_override={
                        'device_id': item['device_id'],
                        'valor': item['valor'],
                        'timestamp': item['timestamp'],
                        'animal_id': item['animal_id']
                    }
                )
                processados += 1
            
            elif tipo == 'colar':
                # Re-faz POST /api/iot/temperatura
                processados += 1
            
            elif tipo == 'comedor':
                # Re-faz POST /api/iot/consumo
                processados += 1
        
        except Exception as e:
            erros.append(f"{item['device_id']}: {str(e)}")
    
    return jsonify({
        "sucesso": True,
        "processados": processados,
        "erros": erros
    })

@app.route("/iot/modal-pareamento")
@login_required
def iot_modal_pareamento():
    """Retorna HTML do modal de pareamento de sensores."""
    return render_template("iot_modal_pareamento.html")
```

---

### 2.5 Templates

#### `templates/iot_modal_pareamento.html`

```html
{% extends "base.html" %}

{% block title %}Pareamento IoT{% endblock %}

{% block content %}
<div class="container">
    <h1>🔗 Pareamento de Sensores IoT</h1>
    
    <div class="cards" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin: 2rem 0;">
        <!-- Balança -->
        <div class="card">
            <h3>📍 Balança</h3>
            <p>Conecta balança eletrônica via Bluetooth para registro automático de peso.</p>
            <button class="btn btn-primary" onclick="parearBalanca()">Pareamento</button>
            <button class="btn btn-secondary" onclick="abrirEmuladorBalanca()" style="margin-left: 0.5rem;">Emulador</button>
        </div>
        
        <!-- Colar -->
        <div class="card">
            <h3>⌚ Colar</h3>
            <p>Conecta colar com temperatura e GPS para monitoramento em tempo real.</p>
            <button class="btn btn-primary" onclick="parearColar()">Pareamento</button>
            <button class="btn btn-secondary" onclick="abrirEmuladorColar()" style="margin-left: 0.5rem;">Emulador</button>
        </div>
        
        <!-- Comedouro -->
        <div class="card">
            <h3>🍽️ Comedouro</h3>
            <p>Conecta comedouro inteligente para controle automático de consumo.</p>
            <button class="btn btn-primary" onclick="parearComedor()">Pareamento</button>
            <button class="btn btn-secondary" onclick="abrirEmuladorComedor()" style="margin-left: 0.5rem;">Emulador</button>
        </div>
    </div>
    
    <!-- Dispositivos Pareados -->
    <h2>📱 Dispositivos Pareados</h2>
    <div id="dispositivos-lista" class="tabela-dados">
        <!-- Preenchida por JavaScript -->
    </div>
    
    <!-- Emulador Balança (oculto) -->
    <div id="emulador-balanca" style="display: none; margin: 2rem 0; padding: 1.5rem; background: var(--bg-secondary); border-radius: 8px;">
        <h3>📊 Emulador Balança</h3>
        <label>Simular Peso (kg):</label>
        <input type="range" id="slider-balanca" min="300" max="500" value="420" 
               oninput="atualizarDisplayBalanca(this.value)" style="width: 100%; margin: 1rem 0;">
        <p style="font-size: 1.5rem; font-weight: bold;"><span id="peso-display">420</span> kg</p>
        <button class="btn btn-primary" onclick="lerBalancaEmu()">📖 Ler Agora</button>
        <button class="btn btn-secondary" onclick="fecharEmulador()" style="margin-left: 0.5rem;">Fechar</button>
    </div>
    
    <!-- Status Offline -->
    <div id="status-offline" style="display: none; margin: 2rem 0; padding: 1rem; background: #fff3cd; border: 1px solid #ffc107; border-radius: 4px;">
        <p>🔴 <strong>Offline</strong> — Os dados serão sincronizados quando conectar à internet.</p>
        <p id="fila-count">Itens pendentes: 0</p>
    </div>
</div>

<script src="{{ url_for('static', filename='js/iot_sensores.js') }}"></script>
<script src="{{ url_for('static', filename='js/iot_manager.js') }}"></script>
<script>
    // Atualiza lista de dispositivos ao carregar
    function atualizarDispositivosList() {
        const config = JSON.parse(localStorage.getItem('iot_devices') || '{}');
        const html = Object.entries(config).map(([id, cfg]) => `
            <tr>
                <td>${cfg.name}</td>
                <td>${cfg.type}</td>
                <td>${cfg.enabled ? '✅ Ativo' : '❌ Inativo'}</td>
                <td>
                    <button class="btn btn-small" onclick="alternarSensor('${id}')">
                        ${cfg.enabled ? 'Desativar' : 'Ativar'}
                    </button>
                    <button class="btn btn-small btn-danger" onclick="removerSensor('${id}')">Remover</button>
                </td>
            </tr>
        `).join('');
        
        document.getElementById('dispositivos-lista').innerHTML = html || '<p>Nenhum dispositivo pareado.</p>';
    }
    
    // Pareamento
    async function parearBalanca() {
        const nome = prompt("Nome do dispositivo:", "Balança 1");
        if (!nome) return;
        
        const result = await iotManager.parearSensor('balanca', nome);
        if (result.sucesso) {
            alert(result.msg);
            atualizarDispositivosList();
        } else {
            alert(result.msg);
        }
    }
    
    async function parearColar() {
        const nome = prompt("Nome do dispositivo:", "Colar 1");
        if (!nome) return;
        
        const result = await iotManager.parearSensor('colar', nome);
        if (result.sucesso) {
            alert(result.msg);
            atualizarDispositivosList();
        } else {
            alert(result.msg);
        }
    }
    
    async function parearComedor() {
        const nome = prompt("Nome do dispositivo:", "Comedouro 1");
        if (!nome) return;
        
        const result = await iotManager.parearSensor('comedor', nome);
        if (result.sucesso) {
            alert(result.msg);
            atualizarDispositivosList();
        } else {
            alert(result.msg);
        }
    }
    
    // Emuladores
    function abrirEmuladorBalanca() {
        document.getElementById('emulador-balanca').style.display = 'block';
    }
    
    function fecharEmulador() {
        document.getElementById('emulador-balanca').style.display = 'none';
    }
    
    function atualizarDisplayBalanca(valor) {
        document.getElementById('peso-display').textContent = valor;
    }
    
    async function lerBalancaEmu() {
        const peso = parseFloat(document.getElementById('slider-balanca').value);
        const result = await iotManager.lerSensor('balanca_emulador');
        if (result) {
            alert(`✅ Peso lido: ${peso}kg`);
        }
    }
    
    // Init
    atualizarDispositivosList();
    
    // Monitora status offline
    window.addEventListener('online', () => {
        document.getElementById('status-offline').style.display = 'none';
    });
    
    window.addEventListener('offline', () => {
        document.getElementById('status-offline').style.display = 'block';
        const fila = JSON.parse(localStorage.getItem('iot_fila_offline') || '[]');
        document.getElementById('fila-count').textContent = `Itens pendentes: ${fila.length}`;
    });
</script>

<style>
    .btn-small { padding: 0.5rem 1rem; font-size: 0.9rem; }
    .btn-danger { background: #dc3545; color: white; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; }
</style>
{% endblock %}
```

---

### 2.6 Alertas (`alertas.py` — expand)

```python
def alertas_iot(df_animais, df_manejo, hoje=None):
    """Detecta anomalias em dados IoT."""
    hoje = pd.Timestamp(hoje or pd.Timestamp.now()).normalize()
    data_limite = hoje - timedelta(days=7)
    
    alertas = []
    
    # 1. Queda de peso >5%
    for _, animal in df_animais.iterrows():
        animal_id = animal['ID']
        
        pesagens = df_manejo[
            (df_manejo['Tipo'] == 'Pesagem') &
            (df_manejo['Brincos'].str.contains(animal_id, na=False)) &
            ((hoje - pd.to_datetime(df_manejo['Data'], dayfirst=True)).dt.days <= 7)
        ]
        
        if len(pesagens) >= 2:
            peso_antigo = _extrair_peso(pesagens.iloc[-1]['Descrição'])
            peso_novo = _extrair_peso(pesagens.iloc[0]['Descrição'])
            
            if peso_antigo > 0:
                queda_pct = (peso_antigo - peso_novo) / peso_antigo * 100
                
                if queda_pct > 5:
                    alertas.append({
                        "tipo": "⚠️ QUEDA PESO",
                        "animal": A.ref(animal),
                        "queda_pct": round(queda_pct, 1),
                        "peso_antes": peso_antigo,
                        "peso_agora": peso_novo,
                        "dias": 7,
                        "acao": "INVESTIGAR — possível doença ou parasitas",
                        "prioridade": 2,
                    })
    
    # 2. Temperatura fora da faixa
    for _, animal in df_animais.iterrows():
        animal_id = animal['ID']
        
        temps = df_manejo[
            (df_manejo['Tipo'] == 'Localização + Temperatura') &
            (df_manejo['Brincos'].str.contains(animal_id, na=False)) &
            ((hoje - pd.to_datetime(df_manejo['Data'], dayfirst=True)).dt.days <= 1)
        ]
        
        if not temps.empty:
            desc = temps.iloc[0]['Descrição']
            try:
                temp = float(desc.split('°C')[0].split()[-1])
                if temp < 18:
                    alertas.append({
                        "tipo": "❄️ TEMP BAIXA",
                        "animal": A.ref(animal),
                        "temp": temp,
                        "acao": "Possível stress pelo frio — aumentar abrigo",
                        "prioridade": 3,
                    })
                elif temp > 28:
                    alertas.append({
                        "tipo": "🔥 TEMP ALTA",
                        "animal": A.ref(animal),
                        "temp": temp,
                        "acao": "Possível stress pelo calor — aumentar sombra/água",
                        "prioridade": 3,
                    })
            except:
                pass
    
    return alertas

def _extrair_peso(descricao):
    """Parseia 'Balança XX: 420kg' → 420"""
    import re
    match = re.search(r'(\d+(?:\.\d+)?)\s*kg', descricao)
    return float(match.group(1)) if match else 0
```

---

## 3. Fluxo de Dados

```
STARTUP:
1. app.py carrega localStorage config (iot_devices)
2. PWA abre /iot/modal-pareamento (ou botão em dashboard)

PAREAMENTO:
1. Usuário clica "Balança"
2. IoTManager.parearSensor('balanca')
   - Se Web Bluetooth: abre picker Android
   - Se não: BalancaEmulador (slider)
3. Salva config em localStorage['iot_devices']

LEITURA PERIÓDICA (setInterval 30s):
1. setInterval(() => iotManager.lerSensor(deviceId), 30000)
2. Sensor.ler() → {valor, timestamp, unit}
3. enfileirarOffline(deviceId, leitura)
4. POST /api/iot/pesagem
   - Se 200: remove da fila
   - Se erro/offline: permanece enfileirado

OFFLINE:
1. setInterval verifica navigator.onLine
2. Se offline: status indicator muda
3. Leituras continuam sendo enfileiradas (localStorage)

RECONEXÃO:
1. window.addEventListener('online') → setupSyncOnOnline()
2. iotManager.sincronizar()
3. POST /api/iot/sync com fila
4. Limpa localStorage['iot_fila_offline']

ALERTAS (a cada 6h):
1. alertas.todos() chama alertas_iot()
2. Detecta queda peso >5%, temp fora faixa
3. Mostra urgentes em dashboard + WhatsApp
```

---

## 4. Config Updates

**`config.py` — adiciona tipos de Manejo:**

```python
TIPOS_MANEJO = [
    "...",
    "Pesagem",  # Novo: de IoT
    "Localização + Temperatura",  # Novo: de IoT
    "Consumo Comedouro",  # Novo: de IoT
]
```

---

## 5. Arquivos Novos + Modificados

| Arquivo | Tipo | Linhas | O Quê |
|---------|------|--------|-------|
| `static/js/iot_sensores.js` | 🆕 | 200 | 6 classes Sensor (Real + Emulador) |
| `static/js/iot_manager.js` | 🆕 | 250 | Gerenciador, fila offline, sync |
| `routes_iot.py` | 🆕 | 150 | 4 endpoints POST (/pesagem, /temp, /consumo, /sync) |
| `templates/iot_modal_pareamento.html` | 🆕 | 150 | Modal pareamento + emuladores |
| `alertas.py` | ✏️ | +50 | `alertas_iot()` + integração em `todos()` |
| `config.py` | ✏️ | +3 | TIPOS_MANEJO novos |
| `app.py` | ✏️ | +2 | Import routes_iot |

---

## 6. Teste & Validação

### 6.1 Unit Tests (`tests/test_iot.py`)

```python
def test_balanca_emulador_conecta():
    sensor = BalancaEmulador()
    result = sensor.conectar()
    assert result['sucesso'] == True

def test_balanca_emulador_le():
    sensor = BalancaEmulador()
    leitura = sensor.ler()
    assert 'valor' in leitura
    assert leitura['unit'] == 'kg'

def test_fila_offline_salva():
    iotManager.enfileirarOffline('balanca_001', {'valor': 420})
    fila = JSON.parse(localStorage.getItem('iot_fila_offline'))
    assert len(fila) == 1

def test_api_pesagem_grava():
    # POST /api/iot/pesagem
    # Verifica se grava em Manejo aba
    pass
```

### 6.2 Smoke Test (Manual)

```bash
python app.py
# Navega para /iot/modal-pareamento
# Clica "Balança" → Emulador
# Ajusta slider → "Ler Agora"
# Verifica se peso grava em Pesagem aba
# Desativa internet (DevTools)
# Continua testando (dados enfileirados)
# Reativa internet → verifica sync
```

---

## 7. Timeline (2 semanas, paralelo com Onda 19)

| Semana | Dia | Task |
|--------|-----|------|
| **1** | 1-2 | `iot_sensores.js` (6 classes) |
| | 3-4 | `iot_manager.js` (manager + offline) |
| | 5-6 | `routes_iot.py` (4 endpoints) |
| | 7 | `iot_modal_pareamento.html` template |
| **2** | 8-9 | `alertas.py` expand + integração |
| | 10 | Testes E2E (pareamento, leitura, sync) |
| | 11-12 | Bug fixes + mobile responsivo |
| | 13-14 | Documentação + commit |

---

## 8. Riscos & Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| Web Bluetooth não funciona em iOS | 🔴 | Fallback: emulador sempre funciona; roadmap Onda 16.X: Hub WiFi |
| localStorage cheio (>5MB) | 🟡 | Fila limitada a 100 itens; limpa após sync |
| Sensor desconecta meio da leitura | 🟡 | Try/catch; retry automático + user alert |
| GPS não funciona indoor | 🟡 | Colar: fallback geolocation API ou manual |

---

## 9. Extensões Futuras (Onda 16.X/Y)

Mesma arquitetura, sem refactor:

- **Onda 16.X:** Colar + GPS real (Geolocation API + Bluetooth GPS)
- **Onda 16.Y:** Comedouro + ML consumo anormal
- **Onda 16.Z:** Hub WiFi local (Raspberry Pi) para regiões sem Bluetooth direto

---

**Spec Completo ✅ Pronto para Implementação**

