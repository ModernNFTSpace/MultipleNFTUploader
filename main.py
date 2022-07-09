if __name__ == "__main__":
    from mnu_utils import get_server_argparser, console
    from mnu_utils.webdriver_setup import download_webdriver
    from mnu_utils.requirements_installer import install_requirements

    from rich.panel import Panel

    from mnu_auditor import scan_env_errors

    parser = get_server_argparser()
    group = parser.add_argument_group("Main")
    group.add_argument("--setup", help="Generate empty configs; Download and patch binary.",
                       action="store_true", default=False)
    group.add_argument("--update-driver", help="Update driver(re-setup)",
                       action="store_true", default=False)
    group.add_argument("--run-driver", help="Run the single 'blank' driver for manual actions. Configs and WebDriver binary must exist before running this command.",
                       action="store_true", default=False)
    group.add_argument("--skip-audit", help="Skip searching for env errors",
                       action="store_true", default=False)

    args = parser.parse_args()

    def setup_webdriver():
        w_version, _ = download_webdriver()
        console.print(
            Panel.fit(
                f"[green]WebDriver v{w_version}[/] was [yellow]downloaded[/] & [orange4]patched[/]",
                padding=(1, 2),
                title=f"[b red]WebDriver info"
            )
        )

    if args.setup:
        from config import gen_empty_configs
        install_requirements()

        msgs = gen_empty_configs()

        console.print(
            Panel.fit(
                "\n".join(msgs),
                padding=(1, 2),
                title=f"[b red]Configs info"
            )
        )
        setup_webdriver()
    elif args.update_driver:
        setup_webdriver()
    elif args.run_driver:
        from driver_init import init_driver_for_manual_actions
        driver = init_driver_for_manual_actions()
        console.log("Driver launched.")
    else:
        if not args.skip_audit:
            scan_env_errors()
        from server import main
        main()
