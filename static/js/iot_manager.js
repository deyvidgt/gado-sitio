/**
 * static/js/iot_manager.js — Gerencia sensores, fila offline, sync automático
 */

class IoTManager {
  constructor() {
    this.sensores = {};
    this.sincronizando = false;
    this.carregarConfiguracao();
  }

  carregarConfiguracao() {
    try {
      const cfg = JSON.parse(localStorage.getItem('iot_devices') || '{}');
      this.sensores = cfg;
    } catch (e) {
      console.error('Erro ao carregar config IoT:', e);
    }
  }

  salvarConfiguracao() {
    localStorage.setItem('iot_devices', JSON.stringify(this.sensores));
  }

  async adicionarFila(tipo, dados) {
    if (!window.offlineSync) throw new Error('Sincronização offline indisponível');
    return window.offlineSync.enqueue({
      url: '/api/iot/sync', metodo: 'POST', tipo,
      dados: {...dados, timestamp: dados.timestamp || new Date().toISOString()}
    });
  }

  async lerSensor(tipo, id_sensor) {
    const cfg_key = `${tipo}_${id_sensor}`;
    const cfg = this.sensores[cfg_key] || {};

    // Escolhe real ou emulador
    let sensor;
    if (cfg.tipo_conexao === 'emulador') {
      if (tipo === 'balanca') sensor = new BalancaEmulador(id_sensor);
      else if (tipo === 'colar') sensor = new ColarEmulador(id_sensor);
      else if (tipo === 'comedouro') sensor = new ComedoroEmulador(id_sensor);
    } else {
      if (tipo === 'balanca') sensor = new BalancaBluetooth(id_sensor);
      else if (tipo === 'colar') sensor = new ColarBluetooth(id_sensor);
      else if (tipo === 'comedouro') sensor = new ComedoroBluetooth(id_sensor);
    }

    if (!sensor) return {sucesso: false, msg: 'Sensor desconhecido'};

    // Conecta e lê
    const conn = await sensor.conectar();
    if (!conn.sucesso) {
      this.adicionarFila(tipo, {msg: conn.msg});
      return conn;
    }

    const leitura = await sensor.ler();
    await sensor.desconectar();

    if (leitura.sucesso) {
      await this.adicionarFila(tipo, leitura);
      return leitura;
    }
    return leitura;
  }

  async sincronizar() {
    if (this.sincronizando || !window.offlineSync) return;
    this.sincronizando = true;
    try { await window.offlineSync.sync(); }
    finally { this.sincronizando = false; }
  }

  iniciarSyncAutomatico(intervalo_ms = 30000) {
    setInterval(() => this.sincronizar(), intervalo_ms);
  }
}

// Exporta para uso global
window.iotManager = new IoTManager();
