{
  branch ? "trunk",
}:

let
  nixpkgs = fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/master.tar.gz";
  };

  pkgs = import nixpkgs { };

  packageLists = import ./package-lists;

  failuresPacked = pkgs.lib.pipe ./results/${branch}/4-failures-packed.csv [
    builtins.readFile
    (pkgs.lib.strings.splitString "\n")
    builtins.tail
    (builtins.map (pkgs.lib.strings.splitString ","))
  ];

  lookupAttrPath = pathStr:
    builtins.foldl'
      (
        acc: path:
          if acc == null then
            null
          else if builtins.hasAttr path acc then
            builtins.getAttr path acc
          else
            null
      )
      pkgs
      (pkgs.lib.strings.splitString "." pathStr);

  getPackage = failure:
    lookupAttrPath (builtins.head failure);

  isMaintainedByConfiguredUser = package:
    let
      maintainers = package.meta.maintainers or [ ];
    in
      pkgs.lib.any (
        maintainer:
          builtins.elem
            (maintainer.github or "")
            packageLists.maintainers
      ) maintainers;

  isExtraPackage = packagePath: package:
    builtins.elem packagePath packageLists.extraPackages
    || builtins.elem
      (package.pname or "")
      packageLists.extraPackages;

  isConcernedFailure = failure:
    let
      packagePath = builtins.head failure;
      evaluated = builtins.tryEval (
        let
          package = getPackage failure;
        in
          package != null
          && (
            isMaintainedByConfiguredUser package
            || isExtraPackage packagePath package
          )
      );
    in
      evaluated.success && evaluated.value;

in
builtins.filter isConcernedFailure failuresPacked
