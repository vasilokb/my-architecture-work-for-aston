📁 auto-insurance/                     (Корневой проект)
├── 📄 .gitignore
├── 📄 .gitlab-ci.yml
├── 📄 Dockerfile
├── 📄 README.md
├── 📄 pom.xml
├── 📁 .m2/
│   └── 📄 settings.xml
├── 📁 travel-db/                      (Модуль работы с БД)
│   ├── 📄 pom.xml
│   └── 📁 src/main/resources/db/
│       ├── 📁 changelog-local/
│       │   ├── 📄 33-fill-travel-claim-fake-data.yml
│       │   └── 📄 db.changelog-local.yml
│       └── 📁 changelog/
│           ├── 📄 changelog-master.yml
│           ├── 📁 v1.0/
│           │   ├── 📄 01-init-db-schema.yaml
│           │   ├── 📄 02-create-travel-program-table.yaml
│           │   ├── 📄 03-create-options-table.yaml
│           │   ├── 📄 04-create-car-table.yaml
│           │   ├── 📄 05-create-car-program-table.yaml
│           │   ├── 📄 06-create-travel-claim-table.yaml
│           │   ├── 📄 07-create-travel-claim-document-table.yaml
│           │   ├── 📄 08-update-travel-insured-people-table.yaml
│           │   ├── 📄 09-update-agreement-table.yaml
│           │   ├── 📄 10-add-country-enum.yaml
│           │   ├── 📄 11-update-travel-insurance-table.yaml
│           │   ├── 📄 12-drop-visitcountry-enum.yaml
│           │   ├── 📄 13-drop-tariff-enum.yaml
│           │   ├── 📄 14-update-travel-agreement-table.yaml
│           │   ├── 📄 15-update-travel-claim-document-table.yaml
│           │   ├── 📄 16-create-aircraft-table.yaml
│           │   ├── 📄 17-create-people-on-board-table.yaml
│           │   ├── 📄 18-create-aviation-program-table.yaml
│           │   ├── 📄 19-update-travel-insurance-table.yaml
│           │   ├── 📄 20-drop-car-program-table.yaml
│           │   ├── 📄 21-drop-car-table.yaml
│           │   ├── 📄 22-drop-car-insurance-type-enum.yaml
│           │   ├── 📄 23-update-travel-program-table.yaml
│           │   ├── 📄 24-drop-travel-insured-people-table.yaml
│           │   ├── 📄 25-generate-agreement-number.yaml
│           │   ├── 📄 26-change-foreign-key-travel-claim-table.yaml
│           │   ├── 📄 27-update-upload-date-claim-document-table.yaml
│           │   ├── 📄 28-add-status-enum.yaml
│           │   ├── 📄 29-create-outbox-table.yaml
│           │   ├── 📄 30-update-constraints-travel-insurance-table.yaml
│           │   ├── 📄 31-update-certificate-number-length.yaml
│           │   ├── 📄 32-add-constraint-to-travel-claim.yaml
│           │   └── 📁 sql/
│           │       ├── 📄 add-constraint-to-travel-insurance.sql
│           │       ├── 📄 alter-certificate-number-length.sql
│           │       ├── 📄 create-agreement-number.sql
│           │       ├── 📄 create-aircraft-type-enum.sql
│           │       ├── 📄 create-car-insurance-type-enum.sql
│           │       ├── 📄 create-claim-status-enum.sql
│           │       ├── 📄 create-country-enum.sql
│           │       ├── 📄 create-document-type-enum.sql
│           │       ├── 📄 create-flight-purpose-enum.sql
│           │       ├── 📄 create-instalment-enum.sql
│           │       ├── 📄 create-set-default-upload-date.sql
│           │       ├── 📄 create-status-enum.sql
│           │       ├── 📄 create-travel-program-type-enum.sql
│           │       ├── 📄 create-upload-date-trigger.sql
│           │       ├── 📄 drop-car-insurance-type-enum.sql
│           │       ├── 📄 drop-tariff-enum.sql
│           │       ├── 📄 drop-visitcountry-enum.sql
│           │       ├── 📄 init-db-enums.sql
│           │       └── 📄 update-constraint-to-travel-insurance.sql
│           └── 📁 v1.1/
│               ├── 📄 01-add-constraint-to-travel-claim-table.yaml
│               └── 📁 sql/
│                   └── 📄 add-constraint-to-travel-claim.sql
├── 📁 travel-domain/                  (Модуль с доменными моделями)
│   ├── 📄 pom.xml
│   └── 📁 src/main/java/ru/astondevs/mycare/
│       ├── 📁 model/
│       │   ├── 📁 entity/
│       │   │   ├── 📄 Aircraft.java
│       │   │   ├── 📄 AviationProgram.java
│       │   │   ├── 📄 Options.java
│       │   │   ├── 📄 Outbox.java
│       │   │   ├── 📄 PeopleOnBoard.java
│       │   │   ├── 📄 TravelAgreement.java
│       │   │   ├── 📄 TravelClaim.java
│       │   │   ├── 📄 TravelClaimDocument.java
│       │   │   ├── 📄 TravelInsurance.java
│       │   │   └── 📄 TravelProgram.java
│       │   └── 📁 enums/
│       │       ├── 📄 AircraftType.java
│       │       ├── 📄 Country.java
│       │       ├── 📄 DocumentType.java
│       │       ├── 📄 FlightPurpose.java
│       │       ├── 📄 Instalment.java
│       │       ├── 📄 InsuranceStatus.java
│       │       ├── 📄 InsuranceType.java
│       │       ├── 📄 PaymentStatus.java
│       │       ├── 📄 Sport.java
│       │       └── 📄 Status.java
│       └── 📁 repository/
│           ├── 📄 OptionsRepository.java
│           ├── 📄 OutboxRepository.java
│           ├── 📄 TravelAgreementRepository.java
│           ├── 📄 TravelClaimDocumentRepository.java
│           ├── 📄 TravelClaimRepository.java
│           ├── 📄 TravelInsuranceRepository.java
│           └── 📄 TravelProgramRepository.java
└── 📁 travel-impl/                    (Основной модуль с реализацией)
├── 📄 pom.xml
├── 📁 src/main/java/ru/astondevs/mycare/
│   ├── 📄 TravelInsuranceApplication.java
│   ├── 📁 controller/
│   │   ├── 📄 TravelAgreementController.java
│   │   ├── 📄 TravelClaimController.java
│   │   └── 📄 TravelInsuranceController.java
│   ├── 📁 dto/
│   │   ├── 📄 OptionsDto.java
│   │   ├── 📄 TravelAgreementDto.java
│   │   ├── 📄 TravelClaimDocumentDto.java
│   │   ├── 📄 TravelClaimDto.java
│   │   ├── 📄 TravelInsuranceDto.java
│   │   ├── 📄 TravelProgramDto.java
│   │   ├── 📁 request/
│   │   │   ├── 📄 AircraftToCreateDto.java
│   │   │   ├── 📄 AviationInsuranceRequest.java
│   │   │   ├── 📄 AviationProgramToCreateDto.java
│   │   │   ├── 📄 PeopleOnBoardToCreateDto.java
│   │   │   ├── 📄 TravelAviationToCreateDto.java
│   │   │   ├── 📄 TravelClaimDocumentRequest.java
│   │   │   ├── 📄 TravelClaimRejectStatusDto.java
│   │   │   ├── 📄 TravelClaimRequest.java
│   │   │   ├── 📄 TravelClaimUpdateStatusDto.java
│   │   │   ├── 📄 TravelInsuranceRequest.java
│   │   │   └── 📄 TravelInsuranceToRenewDto.java
│   │   └── 📁 response/
│   │       ├── 📄 CreateAgreementResponse.java
│   │       ├── 📄 CreateClaimResponse.java
│   │       ├── 📄 InsuranceByIndividualIdResponse.java
│   │       ├── 📄 InsuranceResponse.java
│   │       ├── 📄 TravelAgreementByIdDto.java
│   │       └── 📄 TravelClaimResponseDto.java
│   ├── 📁 exception/
│   │   ├── 📄 AgreementNotFoundException.java
│   │   ├── 📄 ApplicationException.java
│   │   ├── 📄 ClaimNotFoundException.java
│   │   ├── 📄 InsuranceNotFoundException.java
│   │   └── 📄 SerializationException.java
│   ├── 📁 kafka/
│   │   └── 📁 dto/
│   │       └── 📄 TravelClaimOutboxEventDto.java
│   ├── 📁 mapper/
│   │   ├── 📄 OptionsMapper.java
│   │   ├── 📄 TravelAgreementMapper.java
│   │   ├── 📄 TravelClaimDocumentMapper.java
│   │   ├── 📄 TravelClaimMapper.java
│   │   ├── 📄 TravelInsuranceMapper.java
│   │   └── 📄 TravelProgramMapper.java
│   ├── 📁 service/
│   │   ├── 📄 OutboxService.java
│   │   ├── 📄 TravelAgreementService.java
│   │   ├── 📄 TravelClaimService.java
│   │   ├── 📄 TravelInsuranceService.java
│   │   ├── 📁 chain/
│   │   │   ├── 📁 agreement/
│   │   │   │   ├── 📄 AgreementCreateChainPart.java
│   │   │   │   └── 📁 impl/create/
│   │   │   │       ├── 📄 SaveAgreementChainPart.java
│   │   │   │       ├── 📄 SetAgreementNumberChainPart.java
│   │   │   │       └── 📄 TravelInsuranceChainPart.java
│   │   │   ├── 📁 claim/
│   │   │   │   ├── 📄 TravelClaimCreateChainPart.java
│   │   │   │   └── 📁 impl/create/
│   │   │   │       ├── 📄 TravelAgreementChainPart.java
│   │   │   │       ├── 📄 TravelClaimChainPart.java
│   │   │   │       └── 📄 TravelClaimDocumentChainPart.java
│   │   │   ├── 📁 dto/
│   │   │   │   ├── 📄 AgreementCreateProcessDto.java
│   │   │   │   ├── 📄 ClaimCreateProcessDto.java
│   │   │   │   └── 📄 InsuranceCreateProcessDto.java
│   │   │   └── 📁 insurance/
│   │   │       ├── 📄 InsuranceCreateChainPart.java
│   │   │       └── 📁 impl/create/
│   │   │           ├── 📄 CreateOptionsChainPart.java
│   │   │           ├── 📄 CreateTravelInsuranceChainPart.java
│   │   │           └── 📄 CreateTravelProgramChainPart.java
│   │   ├── 📁 impl/
│   │   │   ├── 📄 OutboxProcessorServiceImpl.java
│   │   │   ├── 📄 OutboxServiceImpl.java
│   │   │   ├── 📄 TravelAgreementServiceImpl.java
│   │   │   ├── 📄 TravelClaimServiceImpl.java
│   │   │   └── 📄 TravelInsuranceServiceImpl.java
│   │   ├── 📁 scheduler/
│   │   │   ├── 📄 OutboxProcessorScheduler.java
│   │   │   └── 📄 OutboxProcessorService.java
│   │   └── 📁 util/constants/
│   │       ├── 📄 ConstantsUtil.java
│   │       ├── 📄 ExceptionMessage.java
│   │       └── 📄 TextConstants.java
│   └── 📁 resources/
│       ├── 📄 application-local.yml
│       └── 📄 application.yaml
└── 📁 src/test/
├── 📁 java/ru/astondevs/mycare/
│   ├── 📁 controller/
│   │   └── 📄 TravelClaimControllerTest.java
│   ├── 📁 repository/
│   │   ├── 📄 IntegrationTest.java
│   │   ├── 📄 TravelClaimRepositoryTest.java
│   │   └── 📄 TravelInsuranceRepositoryTest.java
│   ├── 📁 service/
│   │   ├── 📁 chain/agreement/create/
│   │   │   ├── 📄 SaveAgreementChainPartTest.java
│   │   │   ├── 📄 SetAgreementNumberChainPartTest.java
│   │   │   └── 📄 TravelInsuranceChainPartTest.java
│   │   ├── 📁 chain/claim/create/
│   │   │   ├── 📄 TravelAgreementChainPartTest.java
│   │   │   ├── 📄 TravelClaimChainPartTest.java
│   │   │   └── 📄 TravelClaimDocumentChainPartTest.java
│   │   ├── 📁 chain/insurance/create/
│   │   │   ├── 📄 CreateOptionsChainPartTest.java
│   │   │   ├── 📄 CreateTravelInsuranceChainPartTest.java
│   │   │   └── 📄 CreateTravelProgramChainPartTest.java
│   │   └── 📁 impl/
│   │       ├── 📄 TravelAgreementServiceImplTest.java
│   │       ├── 📄 TravelClaimServiceImplIntegrationTest.java
│   │       ├── 📄 TravelClaimServiceImplTest.java
│   │       └── 📄 TravelInsuranceServiceImplTest.java
│   └── 📁 util/
│       ├── 📄 ConstantUtil.java
│       ├── 📄 ObjectMapperUtils.java
│       ├── 📁 dto/
│       │   ├── 📄 TravelInsuranceToRenewUtil.java
│       │   ├── 📁 request/
│       │   │   ├── 📄 TravelClaimRequestUtil.java
│       │   │   └── 📄 TravelInsuranceRequestUtil.java
│       │   └── 📁 response/
│       │       ├── 📄 CreateAgreementResponseUtil.java
│       │       ├── 📄 CreateClaimResponseUtil.java
│       │       ├── 📄 InsuranceResponseUtil.java
│       │       └── 📄 TravelClaimResponseDtoUtil.java
│       └── 📁 model/
│           ├── 📄 TravelAgreementUtil.java
│           ├── 📄 TravelClaimUtil.java
│           └── 📄 TravelInsuranceUtil.java
└── 📁 resources/
├── 📄 application.yaml
├── 📄 init.sql
├── 📄 test.sql
└── 📄 travelAgreementForIndividualId.json

## Ключевые особенности Travel Insurance:

1. **`travel-db/`** - Миграции БД для туристического страхования с поддержкой версионности через Liquibase
2. **`travel-domain/`** - Доменная модель (TravelInsurance, TravelClaim, TravelAgreement, AviationProgram и т.д.)
3. **`travel-impl/`** - Сервис с **Chain of Responsibility** паттерном для создания объектов:
    - `chain/agreement/create/` - создание договоров
    - `chain/claim/create/` - создание страховых случаев
    - `chain/insurance/create/` - создание страховок

4. **Авиационное страхование** - Специализированные сущности:
    - `Aircraft`, `PeopleOnBoard`, `AviationProgram` для авиационного страхования
    - Отдельные DTO для создания авиационных объектов

5. **Outbox паттерн** - Асинхронная обработка событий через Kafka:
    - `Outbox` entity для надежной доставки сообщений
    - Планировщик для обработки исходящих событий

6. **Модульная архитектура** - Четкое разделение:
    - `travel-domain` - сущности и репозитории
    - `travel-impl` - бизнес-логика, контроллеры, DTO
    - `travel-db` - миграции и скрипты БД

7. **Поддержка разных типов программ**:
    - TravelProgram с опциями (Options)
    - AviationProgram для авиационного страхования

8. **Комплексное тестирование** - Интеграционные и модульные тесты:
    - Тесты для chain-обработчиков
    - Тесты репозиториев и сервисов
    - Утилиты для тестовых данных