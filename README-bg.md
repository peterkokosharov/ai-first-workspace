# AI-first workspace

**Първо се обадете.** Отворете тази папка с opencode и напишете в чата една дума —
„здр“, „привет“ или „хало!“ — на родния си език, и в същия ред попитайте как се работи
с това нещо. Ще получите отговор на същия език.

*Други езици: [English](README.md).*

Това е превод на [`README.md`](README.md). Ако двете се разминат, вярно е английското.

**Какво е това:** готова папка за писане на програма (или на книга) заедно с AI агент,
за **$0**. Изтеглете папката, отворете я с **opencode** и неговите безплатни модели, и
агентът намира вътре своите правила, инструменти и списък с модели. Копирайте папката на
друг компютър и работата продължава там.

**За кого е:** за всеки, включително начинаещи, с евтин лаптоп (4-8 GB RAM, Windows 10/11
или Linux Mint). Нищо не пуска модел на компютъра, така че малко памет е достатъчно;
моделите работят в облака, на безплатни нива.

**Какво получавате:**

- Правила, които агентът следва (`AGENTS.md`), така че всеки агент се държи еднакво.
- Сигурно място за ключове за API: ключът остава в собственото хранилище на операционната
  система (Windows Credential Manager, KWallet, GNOME Keyring), никога във файл в тази
  папка.
- Списък с безплатни модели, които може да ползвате (`kb/`), плюс малки инструменти за
  проверка на компютъра, за съхраняване на ключове и за свързване на opencode с моделите.
- Проверка за ключове, която не ви позволява да комитнете ключ по невнимание (git hook;
  иска Python: без Python само предупреждава и пуска комита).

Модели, всички безплатни: собствените безплатни модели на opencode (не искат ключ), около
20 **безплатни модела на NVIDIA** (build.nvidia.com, безплатен акаунт и ключ), и по избор
безплатните планове на Gemini и ChatGPT (те имат строги дневни лимити). Платен доставчик
не е нужен. Списъкът с модели е в [`kb/`](kb/README.md); събран е от build.nvidia.com с
`tools/robota.py` на 2026-11-08, тоест остарява: модели идват и си отиват.

## Начало на Windows (3 стъпки)

Какво да се инсталира първо: [`INSTALL.md`](INSTALL.md), раздел „What the machine needs“.

1. Инсталирайте **Python 3.10 или по-нов** от python.org (носи `py`) и **Git for Windows**
   (носи Git Bash). Инсталирайте **opencode** (https://opencode.ai).
2. Вземете тази папка (`git clone https://github.com/peterkokosharov/ai-first-workspace.git`
   или я разархивирайте), отворете **Git Bash** в нея и изпълнете:
   ```bash
   py tools/autodiscovery.py      # checks your machine
   py tools/inventory.py init     # creates the local list of tools and models
   git config core.hooksPath .githooks   # turns on the secret check
   ```
3. Стартирайте opencode в папката; безплатните му модели работят без ключ. По избор:
   запишете безплатен ключ за NVIDIA (влиза в Windows Credential Manager; вие го въвеждате,
   никъде не се показва), за да имате повече модели:
   ```bash
   opencode
   py tools/secret.py set nvidia/personal/api_key     # optional
   ```

## Начало на Linux (3 стъпки)

Какво да се инсталира първо: [`INSTALL.md`](INSTALL.md), раздел „What the machine needs“.

Цел: Linux Mint (Cinnamon), който пази ключовете в GNOME Keyring през `secret-tool`
(пакет `libsecret-tools`, обикновено вече е там). Досега е тествано на Q4OS (TDE, KWallet).

1. Уверете се, че `python3` (3.10 или по-нов) и `git` са инсталирани
   (`python3 --version`, `git --version`). Инсталирайте **opencode** (https://opencode.ai).
2. Вземете тази папка и изпълнете в нея:
   ```bash
   python3 tools/autodiscovery.py
   python3 tools/inventory.py init
   git config core.hooksPath .githooks
   ```
3. Стартирайте opencode в папката; безплатните му модели работят без ключ. По избор:
   запишете безплатен ключ за NVIDIA (ключодържателят на работния плот се избира сам), за
   да имате повече модели:
   ```bash
   opencode
   python3 tools/secret.py set nvidia/personal/api_key     # optional
   ```

Повече подробности: [`INSTALL.md`](INSTALL.md).

## Агенти

opencode е по подразбиране, защото е безплатен. Останалите също работят с тази папка.

| Агент | Състояние | Откъде чете правилата |
|-------|-----------|-----------------------|
| opencode | тестван (по подразбиране, безплатни модели) | `AGENTS.md` |
| Gemini CLI | тестван (безплатен план с лимити) | `GEMINI.md` (сочи към `AGENTS.md`) |
| goose | тестван | `AGENTS.md` |
| Claude Code | тестван (иска платен план) | `CLAUDE.md` (сочи към `AGENTS.md`) |
| Codex CLI | не е тестван | `AGENTS.md` |

## Свързване на opencode с моделите на NVIDIA (по избор)

```bash
python3 tools/setup_nvidia.py --dry-run   # shows what would change, writes nothing
python3 tools/setup_nvidia.py             # adds the NVIDIA models to opencode's config
python3 tools/run_opencode.py             # start opencode WITH your stored keys
```

(`py` вместо `python3` на Windows.) Ключът **никога не се записва в конфигурацията на
opencode**: конфигурацията само назовава променливата `NVIDIA_API_KEY`. Стартирайте
opencode през `tools/run_opencode.py`: той прочита ключовете ви от хранилището на
операционната система и ги подава само на процеса opencode (не на вашия shell, не във
файл). Всички аргументи отиват към opencode, например
`python3 tools/run_opencode.py run -m nvidia/<model> 'hi'`. Обикновеното `opencode`
продължава да работи за собствените безплатни модели. Други доставчици (Gemini, DeepSeek,
Groq, Mistral, OpenRouter): `python3 tools/setup_providers.py <name>`.

Ако стара конфигурация (или някое от копията ѝ `.bak-*`, или `./opencode.json` в текущата
папка) още съдържа ключ в чист текст, инструментите предупреждават и показват къде, но
никога стойността. Инструментите за настройка махат записите, които по-стари версии са
писали (по един на модел), и литералните ключове на доставчиците, които управляват — но
само след като ключът е в хранилището на операционната система; дотогава ключът остава и
инструментът отпечатва командата, която го записва (`python3 tools/secret.py set <path>`,
която иска стойността). Ключове на други доставчици само се докладват;
`--redact-foreign` ги заменя с заместител. Старите файлове `.bak-*` триете сами.

Ключовете живеят в средата на opencode, тоест програмите, които opencode стартира (shell
команди, инструменти на агента), също могат да ги прочетат. Агентът никога не бива да
отпечатва променливи на средата (`env`, `set`, `printenv`, `echo $NVIDIA_API_KEY`).

Инструментите за настройка могат да се пускат повторно: не искат администраторски права
(без sudo), не променят нищо извън вашата потребителска папка и копират старата
конфигурация непроменена в `<file>.bak-YYYYMMDD-HHMMSS-ffffff`, преди да пишат (на
Linux/macOS четимa само от вас; на Windows с правата по подразбиране). Ако това копие
съдържа ключ в чист текст, инструментът го казва: изтрийте копието, след като ключът е в
хранилището на операционната система. Документацията на opencode сочи
`~/.config/opencode/opencode.json` като глобална конфигурация; инструментите ползват тази
папка на Linux и на Windows (`%USERPROFILE%\.config\opencode`). **Непроверено на Windows:**
документацията не дава път за Windows и това не е тествано с истинска инсталация на
opencode на Windows; ако вашият opencode чете друга папка, задайте `OPENCODE_CONFIG` към
онзи файл, за да пишат инструментите там (страницата с конфигурацията не документира тази
променлива). Също `$XDG_CONFIG_HOME/opencode`, ако е зададена, и `~/.configtde/opencode`
само в TDE сесия.

## Ако моделът зацикли

Безплатни модели като **Big Pickle** (opencode) или **Nemotron Super** понякога мислят
много дълго или се повтарят. Тогава:

1. Натиснете **Stop** (Esc в повечето терминални агенти).
2. Напишете `/init` и го изпратете.
3. Продължете със задачата си.

## Тайни

- Стойностите на ключовете никога не влизат в git, в архива или в който и да е файл на
  проект.
- Хранилището е собственото на операционната система: Windows Credential Manager, macOS
  Keychain, GNOME Keyring (`secret-tool`), KWallet или портфейлът на TDE (DCOP) на Q4OS.
  `tools/secret.py` го избира сам и никога не пада към чист файл.
- `~/SECRETS` е умишленото резервно копие, направено от `secret.py export` (стойности на
  ключове в чист текст, извън проекта). Преместете го на флашка; никога не го слагайте в
  git.
- На Q4OS/TDE портфейлът трябва да е включен и отворен веднъж на ръка, преди `secret.py`
  да може да го ползва (`dcop` е в `/opt/trinity/bin`; `secret.py` го намира).

## Какво има в папката

```text
AGENTS.md      the rules for every agent      CLAUDE.md / GEMINI.md  pointers to AGENTS.md
INSTALL.md     step-by-step install           kb/          the free model list
tools/         small Python tools (stdlib)    lib/kikolib/ vendored secret-store library
data/          inventory schema and seed      doc/         architecture and accessibility pages
docs/procedures/  steps for step-review, commit, release audit, HTML docs, GitHub,
                  orchestration, new project
.claude/       Claude Code skills          .opencode/   opencode commands (both point to docs/procedures/)
out/           reports and audits (not in git)
projects/      your own projects, one folder each (not in this repo's git)
```

Инструменти: `secret.py` (ключове), `inventory.py` (местен SQLite списък с машини,
услуги, доставчици, модели, ключове и проекти), `autodiscovery.py` (проверка на
компютъра), `ping.py` / `ping_direct.py` (проба на модел), `setup_nvidia.py` /
`setup_providers.py` / `opencode_config.py` (свързване на opencode с доставчици),
`run_opencode.py` (стартира opencode с ключовете от хранилището на операционната система),
`robota.py` + `gen_models_xml.py` (обновяване на `kb/`), `secret_scan.py` (проверката при
комит и push), `bundle.py` (ядрото плюс един проект в една папка, за предаване).

Пускане на тестовете: `python3 -m unittest discover -s tools/tests -t . -v` (`py` на
Windows).

Местни настройки: копирайте `settings.json.example` в `settings.json` (не се следи от
git). `tools` държи пълен път или команда за всяка програма (празно = намерена в PATH;
`autodiscovery.py --save` я попълва); `run_opencode.py` и `ping.py` ползват
`tools.opencode`. `git` държи `remote_url`, `remote_user` и `token_key` за стъпките с
GitHub. По-стара секция `runtime` още се чете. Имена на ключове: вижте INSTALL.md, „Key
names“.

## Проекти

Собствената ви работа отива в `projects/<name>/`, по една папка на проект, и всяка папка е
своe собствено git репо: корен в нея, собствен `AGENTS.md`, собствен `doc/`, `tools/` и
собствена история. `projects/` е gitignore-ната тук, така че това репо никога не следи
работа за клиент и историята му не носи имена на чужда работа.

Това е нарочно:

- проектът може да се копира, предаде или продаде като пакет:
  `py tools/bundle.py <name>` слага ядрото и проекта в една папка и пуска тестовете на
  проекта вътре в нея;
- може да се push-не към свой remote (GitHub организация на клиента), без да се пипа това
  репо, а това репо може да се push-не, без да публикува проекта;
- това работно място продължава да работи, ако проектът се изтрие. Проектът обаче има
  нужда от ядрото по време на работа — то е рамката — и пакетът носи ядрото със себе си.

Запишете проект в местния списък с `py tools/inventory.py add-project <name>`. Цялата
процедура, включително какво се проверява преди папка да бъде предадена:
[`docs/procedures/new-project.md`](docs/procedures/new-project.md).

## По избор — местен прокси за модели

Не е нужно за начало. Една тестова машина пускаше местен прокси, съвместим с OpenAI (напр.
LiteLLM на `http://127.0.0.1:8000/v1`), като потребителска услуга пред безплатните модели
на NVIDIA. Работното място не го инсталира и не го изисква. Ако пуснете такъв, дръжте
ключовете му в хранилището на операционната система (`tools/secret.py`), никога във файл в
тази папка.

## Преместване на друг компютър

1. Копирайте или клонирайте папката.
2. Пуснете `autodiscovery.py` и `inventory.py init`, както в стъпките за начало.
3. Запишете ключовете отново с `secret.py set ...` (или импортирайте `~/SECRETS`, после го
   изтрийте).
4. Стартирайте вашия агент.

## Лиценз

MIT — вижте [`LICENSE`](LICENSE).
