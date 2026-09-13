📁 auto-insurance/
├── 📄 .gitignore
├── 📄 .gitlab-ci.yml
├── 📄 Dockerfile
├── 📄 README.md
├── 📄 pom.xml
├── 📁 .m2/
│   └── 📄 settings.xml
├── 📁 auto-db/
│   ├── 📄 pom.xml
│   └── 📁 src/main/resources/db/changelog/
│       ├── 📄 changelog-master.yml
│       └── 📁 v1.0/
│           ├── 📄 01-init-db-schema.yml
│           ├── 📄 02-generate-agreement-number.yml
│           ├── 📄 03-add-column-to-auto-program.yml
│           ├── 📄 04-add-value_enum-to-auto-claim.yml
│           ├── 📄 05-create_outbox_table.yml
│           ├── 📄 06-create_shedlock_table.yml
│           └── 📁 sql/
│               ├── 📄 add-value_enum-to-auto-claim.sql
│               ├── 📄 created_enum_outboxstatus.sql
│               ├── 📄 generate-agreement-number.sql
│               └── 📄 init-db-schema-sql.sql
├── 📁 auto-domain/
│   ├── 📄 pom.xml
│   └── 📁 src/main/java/ru/astondevs/mycare/
│       ├── 📁 model/entity/
│       │   ├── 📄 Auto.java
│       │   ├── 📄 AutoAgreement.java
│       │   ├── 📄 AutoClaimDocument.java
│       │   ├── 📄 AutoInsurance.java
│       │   ├── 📄 AutoInsuranceClaim.java
│       │   ├── 📄 AutoProgram.java
│       │   └── 📄 OutboxEvent.java
│       ├── 📁 model/enums/
│       │   ├── 📄 Category.java
│       │   ├── 📄 ClaimStatus.java
│       │   ├── 📄 DocumentType.java
│       │   ├── 📄 InsuranceStatus.java
│       │   ├── 📄 InsuranceType.java
│       │   ├── 📄 OutboxStatus.java
│       │   ├── 📄 PaymentFrequency.java
│       │   └── 📄 PaymentStatus.java
│       └── 📁 repository/
│           ├── 📄 AutoAgreementRepository.java
│           ├── 📄 AutoClaimDocumentRepository.java
│           ├── 📄 AutoInsuranceClaimRepository.java
│           ├── 📄 AutoInsuranceRepository.java
│           ├── 📄 AutoProgramRepository.java
│           ├── 📄 AutoRepository.java
│           └── 📄 OutboxRepository.java
└── 📁 auto-impl/
    ├── 📄 pom.xml
    └── 📁 src/
        ├── 📁 main/
        │   ├── 📁 java/ru/astondevs/mycare/
        │   │   ├── 📄 CarInsuranceApplication.java
        │   │   ├── 📁 config/
        │   │   │   ├── 📄 KafkaTopicConfig.java
        │   │   │   ├── 📄 OutboxSchedulerProperties.java
        │   │   │   ├── 📄 ShedLockConfig.java
        │   │   │   └── 📄 WebConfig.java
        │   │   ├── 📁 controller/
        │   │   │   ├── 📄 AutoAgreementController.java
        │   │   │   ├── 📄 AutoClaimDocumentController.java
        │   │   │   ├── 📄 AutoInsuranceClaimController.java
        │   │   │   ├── 📄 AutoInsuranceController.java
        │   │   │   └── 📁 impl/
        │   │   │       ├── 📄 AutoAgreementControllerImpl.java
        │   │   │       ├── 📄 AutoClaimDocumentControllerImpl.java
        │   │   │       ├── 📄 AutoInsuranceClaimControllerImpl.java
        │   │   │       └── 📄 AutoInsuranceControllerImpl.java
        │   │   ├── 📁 dto/
        │   │   │   ├── 📁 request/
        │   │   │   │   ├── 📄 AgreementRenewingRequestDto.java
        │   │   │   │   ├── 📄 AutoClaimCreationRequestDto.java
        │   │   │   │   ├── 📄 AutoInsuranceCreateRequest.java
        │   │   │   │   ├── 📄 AutoInsuranceToCreateDto.java
        │   │   │   │   ├── 📄 AutoProgramToCreateDto.java
        │   │   │   │   ├── 📄 AutoToCreateDto.java
        │   │   │   │   └── 📄 ClaimRejectStatusDto.java
        │   │   │   └── 📁 response/
        │   │   │       ├── 📄 AgreementCreationResponseDto.java
        │   │   │       ├── 📄 AutoAgreementInfoResponseDto.java
        │   │   │       ├── 📄 AutoClaimCreationResponseDto.java
        │   │   │       ├── 📄 AutoClaimInfoResponseDto.java
        │   │   │       ├── 📄 DocumentResponseDto.java
        │   │   │       ├── 📄 InsuranceByIndividualIdResponseDto.java
        │   │   │       └── 📄 InsuranceCreationResponseDto.java
        │   │   ├── 📁 exception/
        │   │   │   ├── 📄 AgreementNotFoundException.java
        │   │   │   ├── 📄 ClaimNotFoundException.java
        │   │   │   ├── 📄 DocumentNotFoundException.java
        │   │   │   └── 📄 InsuranceNotFoundException.java
        │   │   ├── 📁 kafka/
        │   │   │   ├── 📄 KafkaService.java
        │   │   │   ├── 📄 KafkaServiceImpl.java
        │   │   │   └── 📁 dto/
        │   │   │       ├── 📄 ClaimNewStatusEvent.java
        │   │   │       ├── 📄 ClaimStatusChangedEvent.java
        │   │   │       ├── 📄 ClaimStatusUpdateDto.java
        │   │   │       └── 📄 NewInsuranceMessage.java
        │   │   ├── 📁 mapper/
        │   │   │   ├── 📄 AutoAgreementMapper.java
        │   │   │   ├── 📄 AutoClaimDocumentMapper.java
        │   │   │   ├── 📄 AutoInsuranceClaimMapper.java
        │   │   │   ├── 📄 AutoInsuranceMapper.java
        │   │   │   ├── 📄 AutoMapper.java
        │   │   │   └── 📄 AutoProgramMapper.java
        │   │   ├── 📁 outbox/
        │   │   │   ├── 📄 OutboxScheduler.java
        │   │   │   └── 📄 OutboxService.java
        │   │   ├── 📁 service/
        │   │   │   ├── 📄 AutoAgreementService.java
        │   │   │   ├── 📄 AutoClaimDocumentService.java
        │   │   │   ├── 📄 AutoInsuranceClaimService.java
        │   │   │   ├── 📄 AutoInsuranceService.java
        │   │   │   ├── 📁 chain/
        │   │   │   │   ├── 📁 agreement/
        │   │   │   │   │   ├── 📁 creation/
        │   │   │   │   │   │   ├── 📄 AgreementCreateChainPart.java
        │   │   │   │   │   │   ├── 📁 dto/
        │   │   │   │   │   │   │   └── 📄 AutoAgreementCreatedProcessDto.java
        │   │   │   │   │   │   └── 📁 impl/
        │   │   │   │   │   │       ├── 📄 CreateAgreementNumberChainPart.java
        │   │   │   │   │   │       ├── 📄 SaveAutoAgreementChainPart.java
        │   │   │   │   │   │       └── 📄 SetAutoInsuranceChainPart.java
        │   │   │   │   │   └── 📁 renewing/
        │   │   │   │   │       ├── 📄 AgreementRenewingChainPart.java
        │   │   │   │   │       ├── 📁 dto/
        │   │   │   │   │       │   └── 📄 AgreementRenewingProcessDto.java
        │   │   │   │   │       └── 📁 impl/
        │   │   │   │   │           ├── 📄 CreatingRenewalInsuranceChainPart.java
        │   │   │   │   │           ├── 📄 GettingInsuranceChainPart.java
        │   │   │   │   │           └── 📄 SavingRenewalInsuranceChainPart.java
        │   │   │   │   ├── 📁 claim/
        │   │   │   │   │   └── 📁 creation/
        │   │   │   │   │       ├── 📄 ClaimCreationChainPart.java
        │   │   │   │   │       ├── 📁 dto/
        │   │   │   │   │       │   └── 📄 AutoClaimCreationChainDto.java
        │   │   │   │   │       └── 📁 impl/
        │   │   │   │   │           ├── 📄 AgreementIdCheckingChainPart.java
        │   │   │   │   │           ├── 📄 ClaimSavingChainPart.java
        │   │   │   │   │           └── 📄 DocumentsSavingChainPart.java
        │   │   │   │   └── 📁 insurance/
        │   │   │   │       └── 📁 creation/
        │   │   │   │           ├── 📄 InsuranceCreateChainPart.java
        │   │   │   │           ├── 📁 dto/
        │   │   │   │           │   └── 📄 AutoInsuranceCreatedProcessDto.java
        │   │   │   │           └── 📁 impl/
        │   │   │   │               ├── 📄 CreateAutoChainPart.java
        │   │   │   │               ├── 📄 CreateAutoInsuranceChainPart.java
        │   │   │   │               └── 📄 CreateAutoProgramChainPart.java
        │   │   │   ├── 📁 client/
        │   │   │   │   └── 📄 MongoDbFeignClient.java
        │   │   │   ├── 📁 impl/
        │   │   │   │   ├── 📄 AutoAgreementServiceImpl.java
        │   │   │   │   ├── 📄 AutoClaimDocumentServiceImpl.java
        │   │   │   │   ├── 📄 AutoInsuranceClaimServiceImpl.java
        │   │   │   │   └── 📄 AutoInsuranceServiceImpl.java
        │   │   │   └── 📁 util/
        │   │   │       └── 📄 ExceptionMessage.java
        │   │   └── 📁 resources/
        │   │       └── 📄 application.yml
        │   └── 📁 test/
        │       ├── 📁 java/ru/astondevs/mycare/
        │       │   ├── 📁 controller/
        │       │   │   ├── 📄 AutoAgreementControllerTest.java
        │       │   │   ├── 📄 AutoClaimDocumentControllerTest.java
        │       │   │   ├── 📄 AutoInsuranceClaimControllerTest.java
        │       │   │   └── 📄 AutoInsuranceControllerTest.java
        │       │   ├── 📁 exception/
        │       │   │   ├── 📄 AgreementNotFoundExceptionTest.java
        │       │   │   ├── 📄 ClaimNotFoundExceptionTest.java
        │       │   │   ├── 📄 DocumentNotFoundExceptionTest.java
        │       │   │   └── 📄 InsuranceNotFoundExceptionTest.java
        │       │   ├── 📁 kafka/
        │       │   │   └── 📄 KafkaServiceImplTest.java
        │       │   ├── 📁 repository/
        │       │   │   ├── 📄 AutoInsuranceRepositoryTest.java
        │       │   │   └── 📄 IntegrationTest.java
        │       │   ├── 📁 service/
        │       │   │   ├── 📄 AutoAgreementServiceImplTest.java
        │       │   │   ├── 📄 AutoClaimDocumentServiceImplTest.java
        │       │   │   ├── 📄 AutoInsuranceClaimServiceImplTest.java
        │       │   │   ├── 📄 AutoInsuranceServiceImplTest.java
        │       │   │   ├── 📄 OutboxSchedulerTest.java
        │       │   │   ├── 📄 OutboxServiceTest.java
        │       │   │   └── 📁 chain/
        │       │   │       ├── 📁 agreement/
        │       │   │       │   ├── 📁 creation/
        │       │   │       │   │   ├── 📄 CreateAgreementNumberChainPartTest.java
        │       │   │       │   │   ├── 📄 SaveAutoAgreementChainPartTest.java
        │       │   │       │   │   └── 📄 SetAutoInsuranceChainPartTest.java
        │       │   │       │   └── 📁 renewing/
        │       │   │       │       └── 📁 impl/
        │       │   │       │           ├── 📄 CreatingRenewalInsuranceChainPartTest.java
        │       │   │       │           ├── 📄 GettingInsuranceChainPartTest.java
        │       │   │       │           └── 📄 SavingRenewalInsuranceChainPartTest.java
        │       │   │       ├── 📁 claim/
        │       │   │       │   └── 📁 impl/
        │       │   │       │       ├── 📄 AgreementIdCheckingChainPartTest.java
        │       │   │       │       ├── 📄 ClaimSavingChainPartTest.java
        │       │   │       │       └── 📄 DocumentsSavingChainPartTest.java
        │       │   │       └── 📁 insurance/
        │       │   │           └── 📁 creation/
        │       │   │               ├── 📄 CreateAutoChainPartTest.java
        │       │   │               ├── 📄 CreateAutoInsuranceChainPartTest.java
        │       │   │               └── 📄 CreateAutoProgramChainPartTest.java
        │       │   ├── 📁 util/
        │       │   │   ├── 📄 ConstantUtil.java
        │       │   │   ├── 📄 JsonTestUtils.java
        │       │   │   ├── 📁 dto/
        │       │   │   │   ├── 📁 chain/
        │       │   │   │   │   ├── 📄 AgreementRenewingProcessDtoUtil.java
        │       │   │   │   │   └── 📄 AutoClaimCreationProcessDtoUtil.java
        │       │   │   │   ├── 📁 request/
        │       │   │   │   │   ├── 📄 AgreementRenewingRequestDtoUtil.java
        │       │   │   │   │   ├── 📄 AutoClaimCreationRequestDtoUtil.java
        │       │   │   │   │   └── 📄 ClaimReviewingRequestDtoUtil.java
        │       │   │   │   └── 📁 response/
        │       │   │   │       ├── 📄 AutoAgreementInfoResponseDtoUtil.java
        │       │   │   │       ├── 📄 AutoClaimInfoResponseDtoUtil.java
        │       │   │   │       ├── 📄 DocumentResponseDtoUtil.java
        │       │   │   │       └── 📄 InsuranceByIndividualIdResponseDtoUtil.java
        │       │   │   └── 📁 model/
        │       │   │       ├── 📄 AutoAgreementUtil.java
        │       │   │       ├── 📄 AutoClaimDocumentUtil.java
        │       │   │       ├── 📄 AutoInsuranceClaimUtil.java
        │       │   │       ├── 📄 AutoInsuranceUtil.java
        │       │   │       ├── 📄 AutoProgramUtil.java
        │       │   │       └── 📄 AutoUtil.java
        │       │   └── 📁 resources/
        │       │       ├── 📄 application.yml
        │       │       ├── 📄 init.sql
        │       │       ├── 📄 test.sql
        │       │       └── 📁 test-data/
        │       │           ├── 📄 auto-claim-request.json
        │       │           └── 📄 reject-request.json


### Пояснения к структуре:

Это **Auto Insurance Service** — система автострахования со сложной бизнес-логикой. Основные особенности:

1. **`auto-db/`** — Модуль миграций Liquibase:
   - Использует итеративные обновления схемы
   - Содержит генераторы номеров договоров
   - Настройки для outbox-паттерна и shedlock

2. **`auto-domain/`** — Доменный слой:
   - **Сущности**: Авто, Страхование, Договор, Претензия, Программы страхования
   - **Enums**: Статусы, типы, категории, частоты платежей
   - **Репозитории**: Spring Data JPA для всех сущностей

3. **`auto-impl/`** — Бизнес-логика и API:
   - **Chain of Responsibility**: Сложные цепочки обработки для создания/продления договоров, обработки претензий
   - **Kafka Integration**: Отправка событий о статусах претензий и новых страховках
   - **Outbox Pattern**: Надежная отправка событий через таблицу outbox
   - **ShedLock**: Координация распределенных задач
   - **REST API**: Полный набор контроллеров для всех бизнес-операций
   - **Тестирование**: Комплексные тесты всех компонентов, включая интеграционные

4. **Ключевые паттерны**:
   - Chain of Responsibility для сложных бизнес-процессов
   - Outbox Pattern для надежной отправки событий
   - CQRS-подобное разделение DTO (request/response)
   - Широкое использование enum для статусов и типов

