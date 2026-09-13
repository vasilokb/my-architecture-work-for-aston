📁 dms-insurance/
├── 📄 .env
├── 📄 .gitignore
├── 📄 .gitlab-ci.yml
├── 📄 docker-compose.yml
├── 📄 Dockerfile
├── 📄 pom.xml
├── 📄 README.md
├── 📄 register-postgres-connector.json
├── 📁 .m2/
│   └── 📄 settings.xml
├── 📁 checkstyle/
│   ├── 📄 checkstyle-suppressions.xml
│   └── 📄 checkstyle.xml
├── 📁 dms-db/
│   ├── 📄 pom.xml
│   └── 📁 src/
│       └── 📁 main/
│           └── 📁 resources/
│               └── 📁 db/
│                   └── 📁 changelog/
│                       ├── 📄 changelog-master.yml
│                       ├── 📁 data/
│                       │   └── 📄 insert-test-dms-program.sql
│                       ├── 📁 v1.0/
│                       │   ├── 📄 01-init-db-schema.yml
│                       │   ├── 📄 02-add-uuid-generation-to-dms-insurance.yml
│                       │   ├── 📄 03-drop-dms-insurance-constraint.yml
│                       │   ├── 📄 04-create-dms-service-schema.yml
│                       │   ├── 📄 05-transfer-to-dms-service-schema.yml
│                       │   ├── 📄 06-created-dms-claim-table.yml
│                       │   ├── 📄 07-add_dms_agreement_number_to_agreement.yml
│                       │   ├── 📄 08-generate-dms-agreement-number.yml
│                       │   ├── 📄 09-drop-column-to-dms-insurance-client-id.yml
│                       │   ├── 📄 10-update-and-set-default-creation-date.yml
│                       │   ├── 📄 11-created_dependent_person_table.yml
│                       │   ├── 📄 12-add_dependent_person_to_insurance.yml
│                       │   ├── 📄 13-add_column_claim_amount_dms_in_dms_claim.yml
│                       │   ├── 📄 14_add_dms_insurance_sumInsurance_to_dms_insurance.yml
│                       │   ├── 📄 15_delete_column_parent_dms_insurance_id_in_dms_insurance.yml
│                       │   ├── 📄 16_create_outbox_table.yml
│                       │   ├── 📄 17_create_shedlock_table.yml
│                       │   ├── 📄 18_fix_outbox_status_column_schema.yml
│                       │   ├── 📄 19-create-enums-for-new-tables.yml
│                       │   ├── 📄 20-create-new-tables.yml
│                       │   ├── 📄 21-transfer-data-to-new-structure.yml
│                       │   ├── 📄 22-create-fk-for-new tables.yml
│                       │   ├── 📄 23-drop-old-fk.yml
│                       │   ├── 📄 24-drop-irrelevant-tables.yml
│                       │   ├── 📄 25-drop-irrelevant-enums.yml
│                       │   ├── 📄 26-drop-dms-program-table.yml
│                       │   ├── 📄 27-rename-dms_claims_v2.yml
│                       │   ├── 📄 28-change-insurance_contract_status-enum.yml
│                       │   ├── 📄 29-drop-application-person.yml
│                       │   ├── 📄 30-change-owner.yml
│                       │   └── 📁 sql/
│                       │       ├── 📄 add_dms_agreement_number_to_agreement.sql
│                       │       ├── 📄 add_dms_insurance_sumInsurance_to_dms_insurance.sql
│                       │       ├── 📄 create-dms-service-schema.sql
│                       │       ├── 📄 created-enums-for-table-dependent-person.sql
│                       │       ├── 📄 created-enums-for-table-dms-payment.sql
│                       │       ├── 📄 created_enum_outboxstatus.sql
│                       │       ├── 📄 generate-dms-agreement-number.sql
│                       │       ├── 📄 init-db-enums.sql
│                       │       ├── 📄 transfer-to-dms-service-schema.sql
│                       │       └── 📄 update_and_set_default_creation_date.sql
│                       └── 📁 v1.1/
│                           ├── 📄 01-refined-core-schema.yml
│                           ├── 📄 02-remove-insured-person-id-from-applications.yml
│                           ├── 📄 03-add-index-to-shedlock-lock-until.yml
│                           ├── 📄 04-add-version-to-insurance-applications.yml
│                           ├── 📄 05-create-client-type-enum.yml
│                           ├── 📄 06-create-table-client.yml
│                           ├── 📄 07-rename_client_table.yml
│                           ├── 📄 08-big-refactoring.yaml
│                           └── 📄 09-refactor-policy-table.yml
├── 📁 dms-domain/
│   ├── 📄 dms-domain.iml
│   ├── 📄 pom.xml
│   └── 📁 src/
│       └── 📁 main/
│           └── 📁 java/
│               └── 📁 ru/
│                   └── 📁 astondevs/
│                       └── 📁 mycare/
│                           ├── 📁 models/
│                           │   ├── 📁 entity/
│                           │   │   ├── 📄 ClaimApplication.java
│                           │   │   ├── 📄 ClaimApplicationDocument.java
│                           │   │   ├── 📄 Client.java
│                           │   │   ├── 📄 DmsProgram.java
│                           │   │   ├── 📄 Document.java
│                           │   │   ├── 📄 InsuranceApplication.java
│                           │   │   ├── 📄 InsuranceContract.java
│                           │   │   ├── 📄 InsuredPerson.java
│                           │   │   ├── 📄 InsuredPersonsDocument.java
│                           │   │   ├── 📄 MedicalFacility.java
│                           │   │   ├── 📄 OutboxEvent.java
│                           │   │   ├── 📄 Policy.java
│                           │   │   └── 📄 PolicyMedicalFacility.java
│                           │   └── 📁 enums/
│                           │       ├── 📄 ClaimApplicationStatus.java
│                           │       ├── 📄 ClientType.java
│                           │       ├── 📄 DmsType.java
│                           │       ├── 📄 DocumentStatus.java
│                           │       ├── 📄 Gender.java
│                           │       ├── 📄 InsuranceApplicationStatus.java
│                           │       ├── 📄 InsuranceContractStatus.java
│                           │       ├── 📄 MedicalFacilitiesType.java
│                           │       ├── 📄 OutboxStatus.java
│                           │       ├── 📄 PolicyStatus.java
│                           │       └── 📄 Status.java
│                           └── 📁 repository/
│                               ├── 📄 ClientRepository.java
│                               ├── 📄 DmsProgramRepository.java
│                               ├── 📄 DocumentRepository.java
│                               ├── 📄 InsuranceApplicationRepository.java
│                               ├── 📄 InsuredPersonRepository.java
│                               ├── 📄 OutboxRepository.java
│                               └── 📄 PolicyRepository.java
├── 📁 dms-impl/
│   ├── 📄 pom.xml
│   └── 📁 src/
│       ├── 📁 main/
│       │   ├── 📁 java/
│       │   │   └── 📁 ru/
│       │   │       └── 📁 astondevs/
│       │   │           └── 📁 mycare/
│       │   │               ├── 📄 DmsInsuranceApplication.java
│       │   │               ├── 📁 config/
│       │   │               │   ├── 📁 openapi/
│       │   │               │   │   └── 📄 OpenApiConfig.java
│       │   │               │   └── 📁 scheduler/
│       │   │               │       ├── 📄 SchedulerConfig.java
│       │   │               │       └── 📄 SchedulerProperties.java
│       │   │               ├── 📁 consumer/
│       │   │               │   └── 📁 outbox/
│       │   │               │       ├── 📄 OutboxDltListener.java
│       │   │               │       └── 📄 OutboxEventAcknowledger.java
│       │   │               ├── 📁 controller/
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   ├── 📄 InsuranceApplicationController.java
│       │   │               │   │   └── 📁 impl/
│       │   │               │   │       └── 📄 InsuranceApplicationControllerImpl.java
│       │   │               │   └── 📁 policy/
│       │   │               │       ├── 📄 PolicyController.java
│       │   │               │       └── 📁 impl/
│       │   │               │           └── 📄 PolicyControllerImpl.java
│       │   │               ├── 📁 dto/
│       │   │               │   ├── 📄 ClientDto.java
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   ├── 📁 request/
│       │   │               │   │   │   ├── 📄 CreateInsuranceApplicationRequest.java
│       │   │               │   │   │   └── 📄 UpdateApplicationStatusRequest.java
│       │   │               │   │   └── 📁 response/
│       │   │               │   │       └── 📄 InsuranceApplicationResponse.java
│       │   │               │   └── 📁 policy/
│       │   │               │       ├── 📁 request/
│       │   │               │       │   ├── 📄 CreatePolicyRequest.java
│       │   │               │       │   └── 📄 UpdatePolicyStatusRequest.java
│       │   │               │       └── 📁 response/
│       │   │               │           └── 📄 PolicyResponse.java
│       │   │               ├── 📁 event/
│       │   │               │   ├── 📄 BaseClientEvent.java
│       │   │               │   ├── 📄 DomainEvent.java
│       │   │               │   ├── 📁 client/
│       │   │               │   │   ├── 📄 ClientChangeEvent.java
│       │   │               │   │   └── 📄 ClientCreateEvent.java
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   ├── 📄 InsuranceApplicationCreatedEvent.java
│       │   │               │   │   └── 📄 InsuranceApplicationStatusChangedEvent.java
│       │   │               │   └── 📁 policy/
│       │   │               │       ├── 📄 PolicyCreatedEvent.java
│       │   │               │       └── 📄 PolicyStatusChangedEvent.java
│       │   │               ├── 📁 exception/
│       │   │               │   ├── 📄 ApplicationNotFoundException.java
│       │   │               │   ├── 📄 ClientNotFoundException.java
│       │   │               │   ├── 📄 DmsProgramNotFoundException.java
│       │   │               │   ├── 📄 DocumentNotFoundException.java
│       │   │               │   ├── 📄 InsuredPersonNotFoundException.java
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   └── 📄 InsuranceApplicationNotFoundException.java
│       │   │               │   ├── 📁 kafka/
│       │   │               │   │   ├── 📄 EventDeserializationException.java
│       │   │               │   │   ├── 📄 EventSerializationException.java
│       │   │               │   │   ├── 📄 MissingOutboxIdException.java
│       │   │               │   │   └── 📄 TopicConfigurationNotFoundException.java
│       │   │               │   └── 📁 policy/
│       │   │               │       └── 📄 PolicyNotFoundException.java
│       │   │               ├── 📁 kafka/
│       │   │               │   └── 📁 consumer/
│       │   │               │       └── 📁 client/
│       │   │               │           └── 📄 ClientEventConsumer.java
│       │   │               ├── 📁 mapper/
│       │   │               │   ├── 📄 ClientMapper.java
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   └── 📄 InsuranceApplicationMapper.java
│       │   │               │   └── 📁 policy/
│       │   │               │       └── 📄 PolicyMapper.java
│       │   │               ├── 📁 service/
│       │   │               │   ├── 📄 ClientService.java
│       │   │               │   ├── 📁 impl/
│       │   │               │   │   └── 📄 ClientServiceImpl.java
│       │   │               │   ├── 📁 insuranceapplication/
│       │   │               │   │   ├── 📄 InsuranceApplicationService.java
│       │   │               │   │   └── 📁 impl/
│       │   │               │   │       └── 📄 InsuranceApplicationServiceImpl.java
│       │   │               │   ├── 📁 outbox/
│       │   │               │   │   ├── 📄 OutboxCleanupScheduler.java
│       │   │               │   │   ├── 📄 OutboxService.java
│       │   │               │   │   └── 📁 impl/
│       │   │               │   │       └── 📄 OutboxServiceImpl.java
│       │   │               │   ├── 📁 policy/
│       │   │               │   │   ├── 📄 PolicyService.java
│       │   │               │   │   └── 📁 impl/
│       │   │               │   │       └── 📄 PolicyServiceImpl.java
│       │   │               │   ├── 📁 topic/
│       │   │               │   │   ├── 📄 TopicService.java
│       │   │               │   │   └── 📁 impl/
│       │   │               │   │       └── 📄 TopicServiceImpl.java
│       │   │               │   └── 📁 util/
│       │   │               │       ├── 📄 ExceptionMessage.java
│       │   │               │       ├── 📁 constants/
│       │   │               │       │   ├── 📄 ApiPath.java
│       │   │               │       │   └── 📄 TextConstants.java
│       │   │               │       └── 📁 kafka/
│       │   │               │           └── 📄 ConsumerRecordHeaderUtils.java
│       │   │               └── 📁 resources/
│       │   │                   └── 📄 application.yml
│       │   └── 📁 test/
│       │       └── 📁 resources/
│       │           ├── 📄 application.yml
│       │           ├── 📄 init.sql
│       │           └── 📄 test.sql
│       └── 📁 init-scripts/
│           └── 📄 init.sql