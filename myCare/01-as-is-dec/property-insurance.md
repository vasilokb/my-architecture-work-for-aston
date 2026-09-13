Вот древовидная структура на основе предоставленного JSON-массива:

```
📁 property-insurance/                  (Корневой проект - страхование имущества)
├── 📄 .gitignore
├── 📄 .gitlab-ci.yml
├── 📄 Dockerfile
├── 📄 pom.xml
├── 📁 .m2/
│   └── 📄 settings.xml
├── 📁 property-db/                    (Модуль миграций БД)
│   ├── 📄 pom.xml
│   └── 📁 src/main/resources/db/changelog/
│       ├── 📄 changelog-master.yml
│       └── 📁 v1.0/
│           ├── 📄 01-init-db-schema.yaml
│           ├── 📄 02-create-building-property-table.yaml
│           ├── 📄 03-create-commercial-property-table.yaml
│           ├── 📄 04-add-fk-columns-to-address.yaml
│           ├── 📄 05-create-insurance-claims-table.yaml
│           ├── 📄 06-create-claim-documents-table.yaml
│           ├── 📄 07-drop-column-of-address-table.yaml
│           ├── 📄 08-modify-address-columns.yaml
│           ├── 📄 09-add-address-columns.yaml
│           ├── 📄 10-add-columns-to-property-insurance.yaml
│           ├── 📄 11-drop-columns-from-apartment-property.yaml
│           ├── 📄 12-add-columns-to-apartment-property.yaml
│           ├── 📄 13-rename-columns-of-agreement-table.yaml
│           ├── 📄 14-create-property-type-table.yaml
│           ├── 📄 15-add-columns-to-house-propety-table.yaml
│           ├── 📄 16-add-index-for-individual-id.yaml
│           ├── 📄 17-modify-tables-to-actual-data.yaml
│           ├── 📄 18-rollback-for-modify-tables.yaml
│           ├── 📄 19-add-gen-random-uuid.yaml
│           ├── 📄 20-add-individual-house-procedure.yaml
│           ├── 📄 21-add-agreement-number-seq-and-func.yaml
│           ├── 📄 22-create-property-table.yaml
│           ├── 📄 23-rollback-drop-property-tables.yaml
│           ├── 📄 24-drop-column-of-property-insurance-table.yaml
│           ├── 📄 25-make-property-agreement-id-pk-and-fk.yaml
│           ├── 📄 26-add-fk-to-property-agreement-id.yaml
│           ├── 📄 27-create-outbox-table.yaml
│           ├── 📄 28-add-columns-to-outbox-table.yaml
│           ├── 📄 29-add-columns-to-property-insurance-table.yaml
│           ├── 📄 30-modify-columns-to-property-table.yaml
│           ├── 📄 31-drop-column-of-insurance-claim-table.yaml
│           ├── 📄 32-add-columns-to-property-insurance-table.yaml
│           └── 📁 sql/
│               ├── 📄 add-agreement-number-sequence.sql
│               ├── 📄 add-commercial-type-enum.sql
│               ├── 📄 add-document-type-enum.sql
│               ├── 📄 add-geography-enum.sql
│               ├── 📄 add-individual-house-procedure.sql
│               ├── 📄 add-program-enum.sql
│               ├── 📄 add-property-type-description.sql
│               ├── 📄 add-risks-enum.sql
│               ├── 📄 add-status-type-enum.sql
│               ├── 📄 add_generate_agreement_number_function.sql
│               ├── 📄 init-db-enums.sql
│               └── 📄 init-db-enums1.sql
├── 📁 property-domain/                (Модуль доменных моделей)
│   ├── 📄 pom.xml
│   └── 📁 src/main/java/ru/astondevs/mycare/
│       ├── 📁 dto/
│       │   ├── 📄 IndividualHouseProcedureDto.java
│       │   ├── 📄 PropertyInsuranceSaveDto.java
│       │   └── 📁 validate/insurancestatus/
│       │       ├── 📄 PendingInsuranceStatus.java
│       │       └── 📄 PendingInsuranceStatusValidator.java
│       ├── 📁 model/
│       │   ├── 📁 entity/
│       │   │   ├── 📄 Address.java
│       │   │   ├── 📄 Agreement.java
│       │   │   ├── 📄 ClaimDocument.java
│       │   │   ├── 📄 InsuranceClaim.java
│       │   │   ├── 📄 Outbox.java
│       │   │   ├── 📄 Property.java
│       │   │   └── 📄 PropertyInsurance.java
│       │   └── 📁 enums/
│       │       ├── 📄 ClaimStatus.java
│       │       ├── 📄 DocumentType.java
│       │       ├── 📄 Geography.java
│       │       ├── 📄 InsuranceStatus.java
│       │       ├── 📄 PaymentFrequency.java
│       │       ├── 📄 PaymentStatus.java
│       │       ├── 📄 Program.java
│       │       ├── 📄 PropertyType.java
│       │       ├── 📄 Risks.java
│       │       ├── 📄 Status.java
│       │       ├── 📄 Usage.java
│       │       └── 📄 WallMaterial.java
│       └── 📁 repository/
│           ├── 📄 AddressRepository.java
│           ├── 📄 AgreementRepository.java
│           ├── 📄 ClaimDocumentRepository.java
│           ├── 📄 InsuranceClaimRepository.java
│           ├── 📄 PropertyInsuranceRepository.java
│           └── 📄 PropertyRepository.java
└── 📁 property-impl/                  (Основной модуль с реализацией)
    ├── 📄 pom.xml
    ├── 📁 src/main/java/ru/astondevs/mycare/
    │   ├── 📄 PropertyImplApplication.java
    │   ├── 📁 controller/
    │   │   ├── 📄 AgreementController.java
    │   │   ├── 📄 BuildingInsuranceController.java
    │   │   ├── 📄 CommercialInsuranceController.java
    │   │   ├── 📄 DocumentController.java
    │   │   ├── 📄 IndividualHouseInsuranceController.java
    │   │   ├── 📄 InsuranceClaimController.java
    │   │   └── 📄 PropertyInsuranceController.java
    │   ├── 📁 dto/
    │   │   ├── 📄 AddressDto.java
    │   │   ├── 📄 AgreementDto.java
    │   │   ├── 📄 ApartmentPropertyDto.java
    │   │   ├── 📄 BuildingPropertyDto.java
    │   │   ├── 📄 ClaimDocumentDto.java
    │   │   ├── 📄 CommercialPropertyDto.java
    │   │   ├── 📄 HousePropertyDto.java
    │   │   ├── 📄 InsuranceClaimDto.java
    │   │   ├── 📄 PropertyInsuranceDto.java
    │   │   ├── 📄 PropertyInsuranceFilterDto.java
    │   │   ├── 📁 request/
    │   │   │   ├── 📄 AgreementRequestBody.java
    │   │   │   ├── 📄 ClaimDocumentRequest.java
    │   │   │   ├── 📄 ConsiderationOfTheInsuranceEventRequestDto.java
    │   │   │   ├── 📄 InsuranceClaimRequest.java
    │   │   │   ├── 📄 InsuranceClaimReviewRequestDto.java
    │   │   │   ├── 📁 apartment/
    │   │   │   │   ├── 📄 ApartmentAddressRequest.java
    │   │   │   │   ├── 📄 ApartmentInsuranceRequestBody.java
    │   │   │   │   ├── 📄 ApartmentPropertyInsuranceRequest.java
    │   │   │   │   └── 📄 ApartmentPropertyRequest.java
    │   │   │   ├── 📁 building/
    │   │   │   │   ├── 📄 BuildingInsuranceRenewRequestBody.java
    │   │   │   │   └── 📄 BuildingInsuranceRequestBody.java
    │   │   │   ├── 📁 commercial/
    │   │   │   │   ├── 📄 CommercialInsuranceRenewRequestBody.java
    │   │   │   │   └── 📄 CommercialInsuranceRequestBody.java
    │   │   │   └── 📁 house/
    │   │   │       ├── 📄 IndividualHouseAddressRequest.java
    │   │   │       ├── 📄 IndividualHouseInsuranceRequestBody.java
    │   │   │       ├── 📄 IndividualHousePropertyInsuranceRequest.java
    │   │   │       └── 📄 IndividualHousePropertyRequest.java
    │   │   ├── 📁 response/
    │   │   │   ├── 📄 AgreementResponseBody.java
    │   │   │   ├── 📄 ClaimDetailsResponseDTO.java
    │   │   │   ├── 📄 ConsiderationOfTheInsuranceEventResponseDto.java
    │   │   │   ├── 📄 DocumentResponse.java
    │   │   │   ├── 📄 InsuranceClaimResponse.java
    │   │   │   ├── 📄 InsuranceClaimReviewResponseDto.java
    │   │   │   ├── 📄 PropertyInsuranceByIndividualIdResponseDto.java
    │   │   │   ├── 📄 PropertyInsuranceCreationResponseDto.java
    │   │   │   ├── 📄 PropertyTypeInsuranceDto.java
    │   │   │   └── 📁 listOfPoliciesOfAnIndividualDto/
    │   │   │       ├── 📄 AddressResponseDto.java
    │   │   │       ├── 📄 PropertyAgreementResponseDto.java
    │   │   │       ├── 📄 PropertyInsuranceResponseDto.java
    │   │   │       └── 📄 PropertyResponseDto.java
    │   │   └── 📁 exception/
    │   │       ├── 📁 badrequest/
    │   │       │   ├── 📄 UncorrectedInsuranceStatusException.java
    │   │       │   └── 📄 UncorrectedReasonForRejectionException.java
    │   │       └── 📁 notfound/
    │   │           ├── 📄 AddressNotFoundException.java
    │   │           ├── 📄 AgreementNotFoundException.java
    │   │           ├── 📄 BuildingPropertyNotFoundException.java
    │   │           ├── 📄 ClaimNotFoundException.java
    │   │           ├── 📄 CommercialPropertyNotFoundException.java
    │   │           ├── 📄 DocumentNotFoundException.java
    │   │           ├── 📄 InsuranceNotFoundException.java
    │   │           ├── 📄 ParentInsuranceNotFoundException.java
    │   │           └── 📄 PropertyInsuranceNotFoundException.java
    │   ├── 📁 mapper/
    │   │   ├── 📄 AddressMapper.java
    │   │   ├── 📄 AgreementMapper.java
    │   │   ├── 📄 ApartmentInsuranceMapper.java
    │   │   ├── 📄 BuildingInsuranceMapper.java
    │   │   ├── 📄 ClaimDocumentMapper.java
    │   │   ├── 📄 CommercialInsuranceMapper.java
    │   │   ├── 📄 IndividualHouseMapper.java
    │   │   ├── 📄 InsuranceClaimMapper.java
    │   │   ├── 📄 PropertyInsuranceMapper.java
    │   │   └── 📄 PropertyMapper.java
    │   ├── 📁 service/
    │   │   ├── 📄 AddressService.java
    │   │   ├── 📄 AgreementService.java
    │   │   ├── 📄 DocumentService.java
    │   │   ├── 📄 InsuranceClaimService.java
    │   │   ├── 📄 PropertyInsuranceService.java
    │   │   └── 📁 impl/
    │   │       ├── 📄 AddressServiceImpl.java
    │   │       ├── 📄 AgreementServiceImpl.java
    │   │       ├── 📄 DocumentServiceImpl.java
    │   │       ├── 📄 InsuranceClaimServiceImpl.java
    │   │       ├── 📄 PropertyInsuranceServiceImpl.java
    │   │       ├── 📁 chain/
    │   │       │   ├── 📁 build/
    │   │       │   │   ├── 📄 BuildingPropertyInsuranceCreateChainPart.java
    │   │       │   │   └── 📁 impl/
    │   │       │   │       ├── 📄 MapAndSaveBuildingPropertyChainPath.java
    │   │       │   │       └── 📄 MapAndSaveBuildingPropertyInsuranceChainPart.java
    │   │       │   ├── 📁 claims/
    │   │       │   │   ├── 📄 InsuranceClaimCreateChainPart.java
    │   │       │   │   └── 📁 impl/
    │   │       │   │       ├── 📄 MapAndSaveClaimDocumentChainPart.java
    │   │       │   │       └── 📄 MapAndSaveInsuranceClaimChainPart.java
    │   │       │   ├── 📁 insurance/
    │   │       │   │   ├── 📄 PropertyInsuranceCreateChainPart.java
    │   │       │   │   └── 📁 impl/
    │   │       │   │       ├── 📄 MapAndSaveAddressChainPart.java
    │   │       │   │       ├── 📄 MapAndSaveApartmentChainPart.java
    │   │       │   │       └── 📄 MapAndSavePropertyInsuranceChainPart.java
    │   │       │   └── 📁 сommercial/
    │   │       │       ├── 📄 CommercialInsuranceCreateChainPart.java
    │   │       │       └── 📁 impl/
    │   │       │           ├── 📄 MapAndSaveCommercialPropertyChainPath.java
    │   │       │           └── 📄 MapAndSaveCommercialPropertyInsuranceChainPart.java
    │   │       └── 📁 dto/
    │   │           ├── 📄 ApartmentInsuranceProcessDto.java
    │   │           ├── 📄 BuildingInsuranceProcessDto.java
    │   │           ├── 📄 CommercialInsuranceProcessDto.java
    │   │           ├── 📄 InsuranceClaimCreateProcessDto.java
    │   │           └── 📄 PropertyInsuranceProcessDto.java
    │   ├── 📁 util/
    │   │   ├── 📄 ConstantsUtil.java
    │   │   └── 📄 DateUtils.java
    │   └── 📁 resources/
    │       └── 📄 application.yml
    └── 📁 src/test/
        ├── 📁 java/ru/astondevs/mycare/
        │   ├── 📁 config/
        │   │   └── 📄 TestContainersConfig.java
        │   ├── 📁 controller/
        │   │   ├── 📄 AgreementControllerTest.java
        │   │   ├── 📄 DocumentControllerTest.java
        │   │   ├── 📄 InsuranceClaimControllerTest.java
        │   │   └── 📄 PropertyInsuranceControllerTest.java
        │   ├── 📁 repository/
        │   │   └── 📄 PropertyInsuranceRepositoryTest.java
        │   ├── 📁 service/impl/
        │   │   ├── 📄 AddressServiceImplTest.java
        │   │   ├── 📄 AgreementServiceImplTest.java
        │   │   ├── 📄 DocumentServiceImplTest.java
        │   │   ├── 📄 InsuranceClaimServiceTest.java
        │   │   ├── 📄 PropertyInsuranceServiceImplTest.java
        │   │   └── 📁 chain/insurance/impl/
        │   │       ├── 📄 MapAndSaveAddressChainPartTest.java
        │   │       ├── 📄 MapAndSaveApartmentChainPartTest.java
        │   │       ├── 📄 MapAndSavePropertyInsuranceChainPartTest.java
        │   │       └── 📁 claim/
        │   │           └── 📄 MapAndSaveInsuranceClaimChainPartTest.java
        │   └── 📁 util/
        │       ├── 📄 ConstUtil.java
        │       ├── 📄 InsuranceClaimTestUtil.java
        │       ├── 📄 InsuranceClaimUtil.java
        │       ├── 📄 ObjectMapperUtils.java
        │       ├── 📄 PropertyInsuranceTestUtil.java
        │       └── 📄 PropertyInsuranceTestUtil.java
        └── 📁 resources/
            ├── 📄 application.yml
            ├── 📄 init.sql
            ├── 📄 propertyAgreementForIndividualId.json
            ├── 📄 propertyInsurance.json
            ├── 📄 propertyInsuranceByIndividualId.json
            └── 📄 test.sql
```

## Ключевые особенности Property Insurance:

1. **`property-db/`** - Миграции БД для имущественного страхования с расширенной структурой таблиц
2. **`property-domain/`** - Доменная модель с поддержкой разных типов недвижимости:
    - `Property`, `PropertyInsurance`, `InsuranceClaim`, `Agreement`
    - Подтипы: `ApartmentProperty`, `BuildingProperty`, `CommercialProperty`, `HouseProperty`

3. **`property-impl/`** - Сервис с **Chain of Responsibility** паттерном для создания разных типов страхования:
    - `chain/insurance/impl/` - создание страховок (квартиры, дома)
    - `chain/build/impl/` - создание строительного страхования
    - `chain/сommercial/impl/` - создание коммерческого страхования
    - `chain/claims/impl/` - создание страховых случаев

4. **Многоуровневая архитектура типов недвижимости**:
    - Отдельные DTO для квартир, домов, коммерческой недвижимости
    - Специализированные контроллеры для каждого типа
    - Индивидуальные мапперы для преобразования

5. **Outbox паттерн** - Поддержка асинхронной обработки событий через `Outbox` entity

6. **Валидация статусов** - Система валидации статусов страхования через аннотации:
    - `PendingInsuranceStatus` и `PendingInsuranceStatusValidator`

7. **Процедурная логика БД** - Хранимые процедуры для генерации номеров договоров:
    - `add-individual-house-procedure.sql`
    - `add_generate_agreement_number_function.sql`

8. **Комплексное тестирование** - Тесты с использованием TestContainers:
    - Интеграционные тесты контроллеров
    - Тесты цепочки обработки (chain)
    - Тесты сервисов и репозиториев

9. **Гибкая система фильтрации** - `PropertyInsuranceFilterDto` для поиска страховок по различным критериям

10. **Поддержка разных программ страхования** - `Program` enum с различными типами страховых программ для недвижимости