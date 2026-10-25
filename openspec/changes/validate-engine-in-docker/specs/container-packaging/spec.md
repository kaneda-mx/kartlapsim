# Spec Delta

## Purpose

Define el contrato de la imagen de contenedor y del contenedor de validación del simulador: entorno fijado y reproducible, ejecución sin privilegios, salida persistente y terminación limpia, para que la misma imagen sirva de base al servicio web posterior.

## ADDED Requirements

### Requirement: Entorno de ejecución fijado

La imagen SHALL instalar las dependencias numéricas desde un archivo de versiones fijadas y SHALL usar exclusivamente paquetes binarios precompilados, sin compilar durante la construcción.

#### Scenario: Construcción de la imagen

- **WHEN** se construye la imagen desde el repositorio
- **THEN** la construcción instala las versiones exactas declaradas y termina con éxito sin compilar código nativo

#### Scenario: Las dependencias no cambian entre ejecuciones

- **WHEN** se ejecuta el contenedor
- **THEN** no se instala ni actualiza ningún paquete en tiempo de ejecución

### Requirement: Ejecución sin privilegios

El contenedor SHALL ejecutar el proceso de simulación como un usuario sin privilegios, y la imagen SHALL NOT contener credenciales, tokens ni secretos.

#### Scenario: Identidad del proceso

- **WHEN** el contenedor está en ejecución
- **THEN** el proceso de simulación no corre como root

#### Scenario: La imagen no transporta secretos

- **WHEN** se inspecciona el contenido de la imagen
- **THEN** no contiene archivos de credenciales, tokens ni variables de entorno con secretos

### Requirement: Directorio de salida escribible y persistente

La imagen SHALL incluir el directorio de salida con propiedad del usuario de ejecución, y los resultados SHALL sobrevivir a la eliminación del contenedor cuando se monte almacenamiento persistente en ese directorio.

#### Scenario: Escritura sin privilegios

- **WHEN** el proceso sin privilegios escribe los resultados en el directorio de salida
- **THEN** la escritura se completa sin error de permisos

#### Scenario: Resultados tras eliminar el contenedor

- **WHEN** se elimina el contenedor después de una ejecución con almacenamiento persistente montado en el directorio de salida
- **THEN** los archivos de resultados siguen disponibles en ese almacenamiento

### Requirement: El contenedor de validación termina

El contenedor de validación SHALL terminar cuando acabe el cálculo, SHALL propagar el código de salida de la simulación y SHALL NOT reiniciarse automáticamente para repetir el cálculo.

#### Scenario: Fin de la validación

- **WHEN** la simulación termina correctamente
- **THEN** el contenedor pasa a estado finalizado con código 0 y no vuelve a arrancar

#### Scenario: Fallo de la validación

- **WHEN** la simulación falla
- **THEN** el contenedor termina con código distinto de 0, el error queda en sus registros y no se reinicia en bucle

### Requirement: Contexto de construcción mínimo

La construcción SHALL excluir del contexto el historial de control de versiones, los artefactos de planificación y la configuración de herramientas, e incluir únicamente el motor, los datos de ejemplo, el ejecutor y las dependencias declaradas.

#### Scenario: Contenido de la imagen

- **WHEN** se inspecciona la imagen construida
- **THEN** no contiene el historial de control de versiones ni los directorios de planificación o de configuración de herramientas

### Requirement: Trazabilidad de la imagen

La imagen SHALL declarar de qué revisión del repositorio se construyó, de forma consultable sin ejecutarla.

#### Scenario: Identificación de la revisión

- **WHEN** se inspeccionan los metadatos de la imagen
- **THEN** indican la revisión del repositorio con la que se construyó

### Requirement: No se publica sin licencia aclarada

La imagen SHALL NOT publicarse en un registro de acceso público mientras no esté aclarada la licencia del código original redistribuido.

#### Scenario: Intento de publicación

- **WHEN** se plantea publicar la imagen en un registro de acceso público y el repositorio de origen no declara licencia
- **THEN** la publicación no se realiza y queda registrada como pendiente de aclarar con el autor original
