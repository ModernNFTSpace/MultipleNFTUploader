if __name__ == "__main__":
    from mnu_utils import get_server_argparser, console
    from mnu_utils.webdriver_setup import download_webdriver
    from mnu_utils.requirements_installer import install_requirements
    from config import gen_empty_configs

    from rich.panel import Panel

    parser = get_server_argparser()
    group = parser.add_argument_group("Main")
    group.add_argument("--setup", help="Generate empty configs; Download and patch binary.",
                       action="store_true", default=False)
    group.add_argument("--update-driver", help="Update driver(re-setup)",
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
    else:
        from server import main
        main()
