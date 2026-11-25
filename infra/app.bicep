// Servicio de tokens y gateway (KrakenD) en Container Apps. Lo despliega el CD (.github/workflows/cd.yml) en cada cambio a main.
// Requiere la plataforma (infra/plataforma.bicep del repositorio ApiFlota). Ver docs/despliegue-azure.md.
//
//   rodar-tokens   interno   emite los tokens (es el ÚNICO que tiene la llave privada)
//   rodar-gateway  PÚBLICO   valida los tokens con las llaves públicas y reenvía a cada servicio
targetScope = 'resourceGroup'

@description('Debe ser el mismo prefijo que usó al crear la plataforma.')
param prefijo string = 'rodar'

param ubicacion string = resourceGroup().location

@description('Imagen completa del gateway, p. ej. rodaracrxxxx.azurecr.io/rodar-gateway:abc123.')
param imagenGateway string

@description('Imagen completa del servicio de tokens.')
param imagenTokens string

// ---------- Del servicio de tokens ----------
@description('Llave privada RSA (PEM en base64). Solo la recibe el servicio de tokens.')
@secure()
param jwtPrivateKeyB64 string

@description('Lista JSON de clientes con el hash de su secreto.')
@secure()
param clientesJson string

// ---------- Del gateway ----------
@description('Llaves PÚBLICAS (JWKS) con las que el gateway valida los tokens.')
@secure()
param jwksJson string

param jwtIssuer string = 'rodar-gateway'
param jwtAudience string = 'rodar'

@description('Vigencia de un token, en segundos.')
param tokenTtlS int = 900

// ---------- Servicios detrás del gateway ----------
// Un servicio queda activo si su URL no está vacía. Los de Flota se calculan solos (mismo entorno);
// los de los otros grupos se indican cuando estén desplegados (si son de otro entorno, use su URL completa).
@description('Nombre de la aplicación del CRUD de Flota en este entorno. Vacío = rutas de /flota desactivadas.')
param nombreAppFlotaCrud string = 'flota-crud'
param nombreAppFlotaMid string = 'flota-mid'

param flotaCrudUrl string = ''
param flotaMidUrl string = ''
param viajesCrudUrl string = ''
param viajesMidUrl string = ''
param cuentasCrudUrl string = ''
param cuentasMidUrl string = ''

@secure()
param flotaCrudSecret string = ''
@secure()
param flotaMidSecret string = ''
@secure()
param viajesCrudSecret string = ''
@secure()
param viajesMidSecret string = ''
@secure()
param cuentasCrudSecret string = ''
@secure()
param cuentasMidSecret string = ''

@description('0 = escala a cero (ahorra, pero la primera petición tarda). 1 = siempre encendido.')
@minValue(0)
@maxValue(2)
param replicasMinimas int = 0

var sufijo = uniqueString(resourceGroup().id)
var nombreAcr = '${prefijo}acr${sufijo}'
var nombreEntorno = '${prefijo}-entorno'
var nombreTokens = 'rodar-tokens'
var nombreGateway = 'rodar-gateway'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: nombreAcr
}

resource entorno 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: nombreEntorno
}

var dominio = entorno.properties.defaultDomain

// Servicios de Flota: si no se indica la URL, se usa la interna del mismo entorno (exige que tengan secreto).
var urlFlotaCrud = !empty(flotaCrudUrl) ? flotaCrudUrl : (empty(flotaCrudSecret) ? '' : 'https://${nombreAppFlotaCrud}.internal.${dominio}')
var urlFlotaMid = !empty(flotaMidUrl) ? flotaMidUrl : (empty(flotaMidSecret) ? '' : 'https://${nombreAppFlotaMid}.internal.${dominio}')

var servicios = [
  { variable: 'FLOTA_CRUD', nombre: 'flota-crud-secret', url: urlFlotaCrud, secreto: flotaCrudSecret }
  { variable: 'FLOTA_MID', nombre: 'flota-mid-secret', url: urlFlotaMid, secreto: flotaMidSecret }
  { variable: 'VIAJES_CRUD', nombre: 'viajes-crud-secret', url: viajesCrudUrl, secreto: viajesCrudSecret }
  { variable: 'VIAJES_MID', nombre: 'viajes-mid-secret', url: viajesMidUrl, secreto: viajesMidSecret }
  { variable: 'CUENTAS_CRUD', nombre: 'cuentas-crud-secret', url: cuentasCrudUrl, secreto: cuentasCrudSecret }
  { variable: 'CUENTAS_MID', nombre: 'cuentas-mid-secret', url: cuentasMidUrl, secreto: cuentasMidSecret }
]
var activos = filter(servicios, s => !empty(s.url) && !empty(s.secreto))

var registro = [
  {
    server: acr.properties.loginServer
    username: acr.listCredentials().username
    passwordSecretRef: 'acr-password'
  }
]
var secretoAcr = {
  name: 'acr-password'
  value: acr.listCredentials().passwords[0].value
}

resource tokens 'Microsoft.App/containerApps@2024-03-01' = {
  name: nombreTokens
  location: ubicacion
  properties: {
    managedEnvironmentId: entorno.id
    configuration: {
      activeRevisionsMode: 'Single'
      // Interno: solo el gateway llega al servicio de tokens (a través de POST /token).
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: registro
      secrets: [
        secretoAcr
        {
          name: 'jwt-private-key'
          value: jwtPrivateKeyB64
        }
        {
          name: 'clientes-json'
          value: clientesJson
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'tokens'
          image: imagenTokens
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            { name: 'JWT_PRIVATE_KEY_B64', secretRef: 'jwt-private-key' }
            { name: 'CLIENTES_JSON', secretRef: 'clientes-json' }
            { name: 'JWT_ISSUER', value: jwtIssuer }
            { name: 'JWT_AUDIENCE', value: jwtAudience }
            { name: 'TOKEN_TTL_S', value: string(tokenTtlS) }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: replicasMinimas
        maxReplicas: 2
      }
    }
  }
}

resource gateway 'Microsoft.App/containerApps@2024-03-01' = {
  name: nombreGateway
  location: ubicacion
  properties: {
    managedEnvironmentId: entorno.id
    configuration: {
      activeRevisionsMode: 'Single'
      // Público: es la única puerta de entrada. Azure pone el certificado HTTPS.
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'
        allowInsecure: false
      }
      registries: registro
      secrets: concat(
        [
          secretoAcr
          {
            name: 'jwks-json'
            value: jwksJson
          }
        ],
        map(activos, s => {
          name: s.nombre
          value: s.secreto
        })
      )
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: imagenGateway
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat(
            [
              { name: 'TOKENS_URL', value: 'https://${tokens.properties.configuration.ingress.fqdn}' }
              { name: 'JWKS_JSON', secretRef: 'jwks-json' }
              { name: 'JWT_ISSUER', value: jwtIssuer }
              { name: 'JWT_AUDIENCE', value: jwtAudience }
            ],
            flatten(map(activos, s => [
              { name: '${s.variable}_URL', value: s.url }
              { name: '${s.variable}_SECRET', secretRef: s.nombre }
            ]))
          )
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8080
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: replicasMinimas
        maxReplicas: 3
      }
    }
  }
}

output urlPublicaGateway string = 'https://${gateway.properties.configuration.ingress.fqdn}'
output urlTokens string = 'https://${tokens.properties.configuration.ingress.fqdn}'
