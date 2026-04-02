resource "github_repository" "project" {
  name                   = var.github_repo
  visibility             = var.github_visibility
  description            = var.repo_description
  has_issues             = true
  has_projects           = false
  has_wiki               = false
  allow_merge_commit     = true
  allow_squash_merge     = true
  allow_rebase_merge     = true
  allow_auto_merge       = false
  delete_branch_on_merge = var.delete_branch_on_merge
  auto_init              = false
}

resource "github_app_installation_repository" "coderabbit" {
  count           = var.enable_coderabbit_installation ? 1 : 0
  installation_id = var.coderabbit_installation_id
  repository      = github_repository.project.name
}
