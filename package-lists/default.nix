{
  maintainers = [
    "iedame"
  ];

  extraPackages = builtins.concatLists [
    (import ./extra-packages.nix)
    (import ./gaming-team.nix)
  ];
}
