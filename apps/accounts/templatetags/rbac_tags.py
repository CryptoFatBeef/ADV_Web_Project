from django import template

register = template.Library()


class HasRoleNode(template.Node):
    def __init__(self, user_var, roles, nodelist):
        self.user_var = user_var
        self.roles = roles
        self.nodelist = nodelist

    def render(self, context):
        user = self.user_var.resolve(context, ignore_failures=True)
        if not user or not getattr(user, 'is_authenticated', False):
            return ''
        if user.role not in self.roles:
            return ''
        return self.nodelist.render(context)


@register.tag('has_role')
def has_role(parser, token):
    bits = token.split_contents()
    if len(bits) < 3:
        raise template.TemplateSyntaxError(
            "%r tag requires a user argument and at least one role" % bits[0]
        )
    user_var = parser.compile_filter(bits[1])
    roles = [bit.strip('\'"') for bit in bits[2:]]
    nodelist = parser.parse(('end_has_role',))
    parser.delete_first_token()
    return HasRoleNode(user_var, roles, nodelist)
