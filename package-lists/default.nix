{
  maintainers = [
    "iedame"
  ];

  extraPackages = builtins.concatLists (map import [
    # General
    ./extra-packages.nix

    # NixOS/Gaming Team Packages
    ./gaming-team.nix

    # AArch64 Linux failures by year
    ./aarch64-linux-2018.nix
    ./aarch64-linux-2020.nix
    ./aarch64-linux-2022.nix
    ./aarch64-linux-2023.nix
    ./aarch64-linux-2024.nix
  ]);
}
