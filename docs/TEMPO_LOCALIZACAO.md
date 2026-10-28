# Previsão do Tempo com Localização Completa (v5.10.1+)

## Como configurar Município e Estado

A previsão do tempo agora exibe **Município, Estado** quando configurado. Existem **3 formas** de localizar o sítio:

### 1. **Configuração Manual (Recomendado)**

Abra o arquivo `sitio_config.json` na pasta de dados do sítio e adicione:

```json
{
  "nome": "Sítio Santo Antonio",
  "municipio": "Uberlândia",
  "estado": "MG"
}
```

**Vantagens:**
- ✅ Preciso (você escolhe exatamente qual é o município)
- ✅ Não precisa de internet no celular
- ✅ Funciona offline

### 2. **Geolocalização do Celular**

Quando o sítio **não tem** coordenadas (latitude/longitude), o sistema pede:
- Toque em **📍 Usar minha localização**
- Autorize o GPS do celular
- A previsão será atualizada com a localização obtida pelo GPS

**Limitação:** mostra a localização do celular, não necessariamente o sítio.

### 3. **Mapa de Pastos (Automático)**

Se você já tem pastos cadastrados no mapa (`/pastos`), o sistema extrai as coordenadas automaticamente da média dos contornos dos pastos — não precisa fazer nada extra.

---

## Estrutura do `sitio_config.json`

Campo | Tipo | Obrigatório? | Descrição
------|------|-------------|----------
`nome` | string | Sim | Nome do sítio (ex: "Sítio Santo Antonio")
`municipio` | string | Não | Nome do município (ex: "Uberlândia")
`estado` | string | Não | Sigla UF (ex: "MG", "SP", "RJ")
`latitude` | number | Não | Coordenada para previsão (ex: -18.97)
`longitude` | number | Não | Coordenada para previsão (ex: -48.27)
`membros` | array | Não | Lista de donos do sítio

**Exemplo completo:**

```json
{
  "nome": "Sítio Santo Antonio",
  "municipio": "Uberlândia",
  "estado": "MG",
  "latitude": -18.9726,
  "longitude": -48.2743,
  "membros": ["Geane", "Deyvid", "Nilson"]
}
```

---

## Onde aparece a localização

- 📍 **Página de Alertas** (`/alertas`) — exibe "Previsão do tempo · Uberlândia, MG"
- 📱 **Geolocalização Mobile** — atualiza ao enviar localização do celular
- 📊 **API** (`/api/alertas`) — retorna campos `municipio` e `estado` no JSON

---

## Dicas

- ✅ Se só preencheu um (municipio OU estado), exibe apenas aquele
- ✅ Sem preenchimento, mostra o nome do sítio ou "Região do sítio"
- ✅ Coordenadas (latitude/longitude) são usadas para a previsão meteorológica; municipio/estado são apenas para exibição

---

## Exemplos de configuração por estado

### São Paulo (SP)
```json
{"municipio": "Ribeirão Preto", "estado": "SP"}
```

### Minas Gerais (MG)
```json
{"municipio": "Uberaba", "estado": "MG"}
```

### Rio de Janeiro (RJ)
```json
{"municipio": "Teresópolis", "estado": "RJ"}
```

---

## Troubleshooting

**P: A localização não aparece na previsão do tempo**  
R: Verifique se:
1. Os campos `municipio` e `estado` estão preenchidos e salvos no `sitio_config.json`
2. Atualize a página (`F5` ou `Ctrl+Shift+R` para limpar cache)
3. A página de alertas está em `/alertas`

**P: Mostra "Região do sítio" em vez do município**  
R: Provavelmente o arquivo `sitio_config.json` não foi encontrado ou tem erro de sintaxe JSON. Salve novamente.

**P: Posso usar coordenadas diferentes da localização visual?**  
R: Sim! Use `latitude` e `longitude` para a previsão meteorológica, e `municipio`/`estado` para exibição. Útil se o sítio fica na divisa ou você quer previsão de um município vizinho.
