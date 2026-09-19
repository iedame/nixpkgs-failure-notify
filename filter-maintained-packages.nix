{
  branch ? "trunk",
}:
let
  nixpkgs = fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/master.tar.gz";
  };

  pkgs = import nixpkgs { };

  failures-packed = pkgs.lib.pipe ./results/${branch}/4-failures-packed.csv [
    builtins.readFile
    (pkgs.lib.strings.splitString "\n")
    builtins.tail
    (builtins.map (pkgs.lib.strings.splitString ","))
  ];

  gh = "iedame";
  extraPackages = import ./extra-packages.nix;
in let
  lookupAttrPath = pathStr:
    builtins.foldl'
    (acc: p:
      if acc == null then null
      else if builtins.hasAttr p acc then builtins.getAttr p acc
      else null)
    pkgs
    (pkgs.lib.strings.splitString "." pathStr);

  isPkgMaintainer = pkg: pkgs.lib.any (m: (m.github or "") == gh) pkg;

  getMaintainers = pkg: pkg.meta.maintainers or [];

  isMaintainer = pkg-build-fail: let
    evald = builtins.tryEval (
      pkgs.lib.pipe pkg-build-fail [
        builtins.head
        lookupAttrPath
        getMaintainers
        isPkgMaintainer
      ]
    );

    in evald.success && evald.value;

  isExtraPkg =
    p:
    let
      evald = builtins.tryEval (
        pkgs.lib.pipe p [
          builtins.head
          lookupAttrPath
          (p: pkgs.lib.any (extra: (p.pname or "") == extra) extraPackages)
        ]
      );
    in
    evald.success && evald.value;

in builtins.filter (p: isMaintainer p || isExtraPkg p) failures-packed
