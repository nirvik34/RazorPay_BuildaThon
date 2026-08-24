package com.agentpay.guard.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Razorpay Blade design tokens — "Developer-First Financial Canvas".
 * Light mode only. Dodger Blue actions on a white canvas with a
 * Prussian Blue institutional accent.
 */
object GuardColors {
    val Background = Color(0xFFFFFFFF)
    val Foreground = Color(0xFF172B4D)
    val Brand = Color(0xFF0D94FB)        // Dodger Blue — primary actions
    val BrandDark = Color(0xFF0B84E0)
    val Muted = Color(0xFF5E6C84)
    val Border = Color(0xFFEBECF0)
    val Card = Color(0xFFFFFFFF)
    val Navy = Color(0xFF012652)         // Prussian Blue — headers, institutional
    val NavyLight = Color(0xFF0A3A73)
    val SubtleBg = Color(0xFFF7F8FA)     // functional gray surface

    val Success = Color(0xFF04DB7C)
    val SuccessBg = Color(0xFFE8FCF3)
    val SuccessBorder = Color(0xFFB8F0D6)
    val SuccessText = Color(0xFF037B49)

    val Danger = Color(0xFFEB5757)
    val DangerBg = Color(0xFFFEF1F1)
    val DangerBorder = Color(0xFFF9C9C9)
    val DangerText = Color(0xFFB3261E)

    val Warning = Color(0xFFF5A623)
    val WarningBg = Color(0xFFFFF8EB)
    val WarningBorder = Color(0xFFF8E3B8)
    val WarningText = Color(0xFF9A6700)

    val Info = Color(0xFF0D94FB)
    val InfoBg = Color(0xFFE8F6FE)
    val InfoBorder = Color(0xFFBBE4FC)
    val InfoText = Color(0xFF0B6FB4)

    val Purple = Color(0xFF0D94FB)       // AI-context blocks use brand blue tint
    val PurpleBg = Color(0xFFE8F6FE)
}

private val BladeColors = lightColorScheme(
    primary = GuardColors.Brand,
    onPrimary = Color.White,
    secondary = GuardColors.Navy,
    onSecondary = Color.White,
    background = GuardColors.Background,
    onBackground = GuardColors.Foreground,
    surface = GuardColors.Card,
    onSurface = GuardColors.Foreground,
    surfaceVariant = GuardColors.SubtleBg,
    onSurfaceVariant = GuardColors.Muted,
    error = GuardColors.Danger,
    outline = GuardColors.Border
)

/** Mulish voice: clean, technical. Mono for IDs and amounts ("engineered" data). */
val GuardTypography = Typography(
    headlineSmall = TextStyle(
        fontWeight = FontWeight.Bold,
        fontSize = 22.sp,
        letterSpacing = (-0.01).sp
    ),
    titleMedium = TextStyle(
        fontWeight = FontWeight.Bold,
        fontSize = 15.sp,
        letterSpacing = (-0.01).sp
    ),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 21.sp),
    bodySmall = TextStyle(fontSize = 12.sp, lineHeight = 18.sp),
    labelSmall = TextStyle(
        fontFamily = FontFamily.Monospace,
        fontSize = 11.sp
    )
)

@Composable
fun AgentPayTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = BladeColors,
        typography = GuardTypography,
        content = content
    )
}
