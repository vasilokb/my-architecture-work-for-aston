Вот древовидная структура на основе предоставленного JSON-массива:

```
📁 employee-service/                   (Сервис управления сотрудниками)
├── 📄 .gitignore
├── 📄 .gitlab-ci.yml
├── 📄 Dockerfile
├── 📄 README.md
├── 📄 pom.xml
├── 📁 .idea/
│   └── 📄 .gitignore
├── 📁 .m2/
│   └── 📄 settings.xml
├── 📁 checkstyle/                     (Конфигурация стиля кода)
│   ├── 📄 checkstyle-suppressions.xml
│   └── 📄 checkstyle.xml
├── 📁 employee-db/                    (Модуль миграций БД)
│   ├── 📄 pom.xml
│   └── 📁 src/main/resources/db/changelog/
│       ├── 📄 changelog-master.yml
│       └── 📁 v1.0/
│           ├── 📄 01-init-db-schema.yml
│           ├── 📄 02-recreate-employeerole.yml
│           ├── 📄 03-delete-old-db-schema.yml
│           ├── 📄 04-init-db-schema-update.yml
│           ├── 📄 05-alter-table-employees.yml
│           ├── 📄 06-create-indexes.yml
│           └── 📁 sql/
│               ├── 📄 02-recreate-employeerole.sql
│               ├── 📄 03-delete-old-db-schema.sql
│               ├── 📄 04-update-db-schema.sql
│               ├── 📄 05-alter-table-employees.sql
│               ├── 📄 06-create-indexes.sql
│               └── 📄 init-db-schema.sql
├── 📁 employee-domain/                (Модуль доменных моделей)
│   ├── 📄 pom.xml
│   └── 📁 src/main/java/ru/astondevs/mycare/
│       └── 📁 model/
│           ├── 📁 entity/
│           │   ├── 📄 Address.java
│           │   ├── 📄 ContactNumber.java
│           │   ├── 📄 Department.java
│           │   ├── 📄 Employee.java
│           │   ├── 📄 EmployeeAddress.java
│           │   ├── 📄 EmployeePassport.java
│           │   ├── 📄 FcmToken.java
│           │   └── 📄 Office.java
│           ├── 📁 enums/
│           │   ├── 📄 AddressType.java
│           │   ├── 📄 Component.java
│           │   ├── 📄 EmployeeRole.java
│           │   ├── 📄 Gender.java
│           │   ├── 📄 NumberType.java
│           │   ├── 📄 OperatingMode.java
│           │   └── 📄 Status.java
│           └── 📁 repository/
│               ├── 📄 ContactNumberRepository.java
│               ├── 📄 DepartmentRepository.java
│               ├── 📄 EmployeeAddressRepository.java
│               ├── 📄 EmployeeRepository.java
│               ├── 📄 OfficeRepository.java
│               └── 📄 PassportRepository.java
└── 📁 employee-impl/                  (Основной модуль с реализацией)
    ├── 📄 pom.xml
    ├── 📁 src/main/java/ru/astondevs/mycare/
    │   ├── 📄 EmployeeServiceApplication.java
    │   ├── 📁 config/
    │   │   ├── 📄 KeycloakConfig.java
    │   │   ├── 📄 RedisConfig.java
    │   │   └── 📄 RestConfig.java
    │   ├── 📁 controller/
    │   │   ├── 📄 EmployeeController.java
    │   │   ├── 📄 SecurityController.java
    │   │   └── 📁 impl/
    │   │       ├── 📄 EmployeeControllerImpl.java
    │   │       └── 📄 SecurityControllerImpl.java
    │   ├── 📁 dto/
    │   │   ├── 📁 address/
    │   │   │   ├── 📁 request/
    │   │   │   │   ├── 📄 AddressRequestDto.java
    │   │   │   │   └── 📄 UpdateAddressesForEmployeeRequestDto.java
    │   │   │   └── 📁 response/
    │   │   │       ├── 📄 AddressResponseDto.java
    │   │   │       └── 📄 UpdateAddressesForEmployeeResponseDto.java
    │   │   ├── 📁 auth/
    │   │   │   ├── 📁 request/
    │   │   │   │   ├── 📄 AuthorizePhoneRequestDto.java
    │   │   │   │   ├── 📄 AuthorizeRequestDto.java
    │   │   │   │   ├── 📄 RegisterEmployeeRequestDto.java
    │   │   │   │   ├── 📄 Submit2faRequestDto.java
    │   │   │   │   └── 📄 Verify2faRequestDto.java
    │   │   │   └── 📁 response/
    │   │   │       ├── 📄 AuthorizeResponseDto.java
    │   │   │       ├── 📄 EmployeeInfoResponseDto.java
    │   │   │       ├── 📄 QrResponseDto.java
    │   │   │       ├── 📄 Submit2faResponseDto.java
    │   │   │       ├── 📄 UserInfoResponseDto.java
    │   │   │       └── 📄 Verify2faResponseDto.java
    │   │   ├── 📁 employee/
    │   │   │   ├── 📁 request/
    │   │   │   │   ├── 📄 ChangeProfileRequestDto.java
    │   │   │   │   └── 📁 update/
    │   │   │   │       ├── 📄 AddressUpdateRequestDto.java
    │   │   │   │       ├── 📄 EmployeeAddressInfoUpdateRequestDto.java
    │   │   │   │       ├── 📄 EmployeeContactInfoUpdateRequestDto.java
    │   │   │   │       ├── 📄 EmployeeOfficeInfoUpdateRequestDto.java
    │   │   │   │       ├── 📄 EmployeePassportInfoUpdateRequestDto.java
    │   │   │   │       ├── 📄 EmployeePersonalInfoUpdateRequestDto.java
    │   │   │   │       └── 📄 EmployeeProfileFullUpdateRequestDto.java
    │   │   │   └── 📁 response/
    │   │   │       ├── 📄 AddressDto.java
    │   │   │       ├── 📄 AddressesDto.java
    │   │   │       ├── 📄 BaseEmployeeDto.java
    │   │   │       ├── 📄 ContactsDto.java
    │   │   │       ├── 📄 EmployeeBriefInfoDto.java
    │   │   │       ├── 📄 EmployeeDto.java
    │   │   │       ├── 📄 EmployeeProfileDto.java
    │   │   │       ├── 📄 EmployeeProfileFullResponseDto.java
    │   │   │       ├── 📄 MessageUserResponseDto.java
    │   │   │       ├── 📄 OfficeDto.java
    │   │   │       ├── 📄 PassportDataDto.java
    │   │   │       ├── 📄 PersonalDataDto.java
    │   │   │       ├── 📄 PersonalInformationBlockDto.java
    │   │   │       └── 📄 SettingsDto.java
    │   │   ├── 📁 passport/
    │   │   │   ├── 📁 request/
    │   │   │   │   ├── 📄 PassportRequestDto.java
    │   │   │   │   └── 📄 PassportUpdateRequestDto.java
    │   │   │   └── 📁 response/
    │   │   │       └── 📄 PassportResponseDto.java
    │   │   └── 📁 security/
    │   │       ├── 📁 request/
    │   │       │   └── 📄 ChangePasswordRequestDto.java
    │   │       └── 📁 response/
    │   │           ├── 📄 ChangePasswordResponseDto.java
    │   │           └── 📄 RefreshTokenResponseDto.java
    │   ├── 📁 exception/
    │   │   ├── 📁 auth/
    │   │   │   ├── 📄 AuthenticationFailedException.java
    │   │   │   ├── 📄 InvalidKeycloakIdException.java
    │   │   │   ├── 📄 InvalidPasswordException.java
    │   │   │   ├── 📄 KeycloakAccessTokenException.java
    │   │   │   ├── 📄 KeycloakGetQrException.java
    │   │   │   ├── 📄 KeycloakSubmit2FaException.java
    │   │   │   ├── 📄 KeycloakUserCreationException.java
    │   │   │   ├── 📄 KeycloakUserDeletionException.java
    │   │   │   ├── 📄 KeycloakUserNotFoundException.java
    │   │   │   ├── 📄 KeycloakUserUpdateException.java
    │   │   │   ├── 📄 LogoutFailedException.java
    │   │   │   ├── 📄 PassportNotFoundException.java
    │   │   │   └── 📄 VerificationFailedException.java
    │   │   ├── 📁 general/
    │   │   │   ├── 📄 AddressNotFoundException.java
    │   │   │   ├── 📄 BlankUsernameException.java
    │   │   │   ├── 📄 ContactsNotFoundException.java
    │   │   │   ├── 📄 DepartmentNotFoundException.java
    │   │   │   ├── 📄 EmployeeNotFoundException.java
    │   │   │   ├── 📄 OfficeNotFoundException.java
    │   │   │   └── 📄 UserAlreadyExistsException.java
    │   │   └── 📁 security/
    │   │       ├── 📄 BlankAccessTokenException.java
    │   │       ├── 📄 InvalidRefreshTokenException.java
    │   │       ├── 📄 RoleNotFoundException.java
    │   │       └── 📄 UserDisabledException.java
    │   ├── 📁 mapper/
    │   │   ├── 📄 AddressMapper.java
    │   │   ├── 📄 EmployeeMapper.java
    │   │   ├── 📄 EmployeeUpdateMappings.java
    │   │   └── 📄 PassportMapper.java
    │   ├── 📁 service/
    │   │   ├── 📄 ContactNumberService.java
    │   │   ├── 📄 EmployeeAddressService.java
    │   │   ├── 📄 EmployeeService.java
    │   │   ├── 📄 KeycloakService.java
    │   │   ├── 📄 PassportService.java
    │   │   ├── 📄 SecurityService.java
    │   │   └── 📁 impl/
    │   │       ├── 📄 AddressServiceImpl.java
    │   │       ├── 📄 ContactNumberServiceImpl.java
    │   │       ├── 📄 EmployeeServiceImpl.java
    │   │       ├── 📄 KeycloakServiceImpl.java
    │   │       ├── 📄 PassportServiceImpl.java
    │   │       └── 📄 SecurityServiceImpl.java
    │   └── 📁 util/
    │       ├── 📄 ConstantsUtil.java
    │       ├── 📄 CookieUtil.java
    │       ├── 📄 KeycloakUtil.java
    │       ├── 📄 UUIDUtils.java
    │       ├── 📁 annotation/
    │       │   ├── 📄 MinAge.java
    │       │   └── 📄 MinDate.java
    │       └── 📁 validation/
    │           ├── 📄 MinAgeValidator.java
    │           ├── 📄 MinDateValidator.java
    │           ├── 📄 NotBeforeYear.java
    │           └── 📄 NotBeforeYearValidator.java
    ├── 📁 src/main/resources/
    │   ├── 📄 application.yml
    │   └── 📄 banner.txt
    └── 📁 src/test/java/ru/astondevs/mycare/
        ├── 📁 controller/impl/
        │   ├── 📄 EmployeeControllerImplTest.java
        │   └── 📄 SecurityControllerImplTest.java
        ├── 📁 service/impl/
        │   ├── 📄 AddressServiceImplTest.java
        │   ├── 📄 ContactNumberServiceImplTest.java
        │   ├── 📄 EmployeeServiceImplTest.java
        │   ├── 📄 KeycloakServiceImplTest.java
        │   ├── 📄 PassportServiceImplTest.java
        │   └── 📄 SecurityServiceImplTest.java
        └── 📁 service/impl/utils/dto/
            └── 📄 PersonalInformationBlockDtoTestData.java
```

## Ключевые особенности Employee Service:

1. **`employee-db/`** - Миграции БД для управления сотрудниками с итеративными обновлениями схемы

2. **`employee-domain/`** - Комплексная доменная модель для управления сотрудниками:
    - **Основные сущности**:
        - `Employee` - основная информация о сотруднике
        - `Department` - отделы/департаменты
        - `Office` - офисы
        - `EmployeeAddress` - адреса сотрудников
        - `EmployeePassport` - паспортные данные
        - `ContactNumber` - контактные номера
        - `FcmToken` - токены для push-уведомлений
    - **Специализированные перечисления**:
        - `EmployeeRole` - роли сотрудников (админ, менеджер и т.д.)
        - `AddressType` - типы адресов (регистрация, проживание)
        - `NumberType` - типы телефонов (рабочий, личный)
        - `Gender` - пол сотрудника
        - `Status` - статусы сотрудников

3. **`employee-impl/`** - Модуль с расширенной функциональностью:
    - **Интеграция с Keycloak** для управления аутентификацией и авторизацией
    - **Redis** для кэширования и управления сессиями
    - **Двухфакторная аутентификация (2FA)** с QR-кодами

4. **Безопасность и аутентификация**:
    - Полная интеграция с Keycloak Identity Provider
    - Поддержка OAuth2 и JWT токенов
    - Двухфакторная аутентификация
    - Управление паролями и сессиями

5. **Комплексная система DTO**:
    - Разделение на request/response DTO для разных операций
    - Специализированные DTO для обновления профиля сотрудника
    - DTO для аутентификации и безопасности

6. **Расширенная система валидации**:
    - Кастомные аннотации валидации (`@MinAge`, `@MinDate`)
    - Валидаторы для проверки возраста и дат
    - Проверка соответствия бизнес-правилам

7. **Управление профилями сотрудников**:
    - Полное управление персональными данными
    - Адресная информация с разными типами адресов
    - Паспортные данные
    - Контактная информация
    - Информация об офисах и отделах

8. **Тестирование**:
    - Комплексные тесты контроллеров и сервисов
    - Тестовые данные для DTO
    - Интеграционные тесты с Keycloak

9. **Дополнительные функции**:
    - Поддержка push-уведомлений через FCM
    - Управление cookie для веб-приложений
    - Утилиты для работы с UUID и константами

10. **Конфигурация и инструменты**:
    - Конфигурация Checkstyle для поддержания качества кода
    - Конфигурация Keycloak и Redis
    - Настройка REST клиентов

**Примечание**: Этот сервис представляет собой полноценную систему управления сотрудниками с сильным акцентом на безопасность и аутентификацию, в отличие от других модулей, которые сосредоточены на бизнес-логике страхования.